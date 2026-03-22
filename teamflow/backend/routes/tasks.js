const express = require('express');
const router = express.Router();
const Task = require('../models/Task');
const Team = require('../models/Team');
const { protect } = require('../middleware/auth');

// Helper: check if user is leader of their team
const requireLeader = (req, res, next) => {
  if (req.user.role !== 'leader') {
    return res.status(403).json({ message: 'Only team leaders can perform this action' });
  }
  next();
};

// POST /api/tasks - Create a new task (leader only)
router.post('/', protect, requireLeader, async (req, res) => {
  try {
    const { title, description } = req.body;
    if (!title) return res.status(400).json({ message: 'Task title is required' });

    if (!req.user.teamId) {
      return res.status(400).json({ message: 'You must be in a team to create tasks' });
    }

    const taskCount = await Task.countDocuments({ teamId: req.user.teamId });
    const order = taskCount + 1;

    // First task is active; rest are locked
    const status = taskCount === 0 ? 'active' : 'locked';

    const task = await Task.create({
      teamId: req.user.teamId,
      title,
      description: description || '',
      order,
      status,
    });

    // Emit via Socket.io (attached to req.app)
    const io = req.app.get('io');
    if (io) {
      io.to(req.user.teamId.toString()).emit('task:created', task);
    }

    res.status(201).json(task);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// GET /api/tasks - Get all tasks for the current user's team
router.get('/', protect, async (req, res) => {
  try {
    if (!req.user.teamId) {
      return res.status(400).json({ message: 'You must be in a team' });
    }

    const tasks = await Task.find({ teamId: req.user.teamId })
      .sort({ order: 1 })
      .populate('completedBy', 'name email');

    res.json(tasks);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// PATCH /api/tasks/:id/complete - Mark a task as completed by current user
router.patch('/:id/complete', protect, async (req, res) => {
  try {
    const task = await Task.findById(req.params.id).populate('completedBy', 'name email');
    if (!task) return res.status(404).json({ message: 'Task not found' });

    if (task.teamId.toString() !== req.user.teamId?.toString()) {
      return res.status(403).json({ message: 'Task does not belong to your team' });
    }

    if (task.status !== 'active') {
      return res.status(400).json({ message: 'This task is not currently active' });
    }

    const alreadyCompleted = task.completedBy.some(
      (u) => u._id.toString() === req.user._id.toString()
    );
    if (alreadyCompleted) {
      return res.status(400).json({ message: 'You have already completed this task' });
    }

    task.completedBy.push(req.user._id);

    const team = await Team.findById(req.user.teamId);
    const totalMembers = team.members.length;

    let nextUnlocked = null;

    // If all members completed → mark task complete and unlock next
    if (task.completedBy.length >= totalMembers) {
      task.status = 'completed';

      const nextTask = await Task.findOne({
        teamId: req.user.teamId,
        order: task.order + 1,
      });

      if (nextTask) {
        nextTask.status = 'active';
        await nextTask.save();
        nextUnlocked = nextTask;
      }
    }

    await task.save();

    const updatedTask = await Task.findById(task._id).populate('completedBy', 'name email');

    const io = req.app.get('io');
    if (io) {
      io.to(req.user.teamId.toString()).emit('task:updated', updatedTask);
      if (nextUnlocked) {
        const populated = await Task.findById(nextUnlocked._id).populate('completedBy', 'name email');
        io.to(req.user.teamId.toString()).emit('task:unlocked', populated);
      }
    }

    res.json(updatedTask);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// DELETE /api/tasks/:id - Delete a task (leader only)
router.delete('/:id', protect, requireLeader, async (req, res) => {
  try {
    const task = await Task.findById(req.params.id);
    if (!task) return res.status(404).json({ message: 'Task not found' });

    if (task.teamId.toString() !== req.user.teamId?.toString()) {
      return res.status(403).json({ message: 'Task does not belong to your team' });
    }

    await task.deleteOne();

    // Re-order remaining tasks
    const remaining = await Task.find({ teamId: req.user.teamId }).sort({ order: 1 });
    for (let i = 0; i < remaining.length; i++) {
      remaining[i].order = i + 1;
      await remaining[i].save();
    }

    const io = req.app.get('io');
    if (io) {
      io.to(req.user.teamId.toString()).emit('task:deleted', { taskId: req.params.id });
    }

    res.json({ message: 'Task deleted' });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

module.exports = router;
