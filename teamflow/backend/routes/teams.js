const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');
const Team = require('../models/Team');
const User = require('../models/User');
const Task = require('../models/Task');
const { protect } = require('../middleware/auth');

// POST /api/teams - Create a new team (user becomes leader)
router.post('/', protect, async (req, res) => {
  try {
    const { name } = req.body;
    if (!name) return res.status(400).json({ message: 'Team name is required' });

    if (req.user.teamId) {
      return res.status(400).json({ message: 'You are already in a team' });
    }

    const inviteCode = uuidv4().slice(0, 8).toUpperCase();
    const team = await Team.create({
      name,
      leaderId: req.user._id,
      members: [req.user._id],
      inviteCode,
    });

    await User.findByIdAndUpdate(req.user._id, {
      teamId: team._id,
      role: 'leader',
    });

    res.status(201).json(team);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// POST /api/teams/join - Join a team using invite code
router.post('/join', protect, async (req, res) => {
  try {
    const { inviteCode } = req.body;
    if (!inviteCode) return res.status(400).json({ message: 'Invite code is required' });

    if (req.user.teamId) {
      return res.status(400).json({ message: 'You are already in a team' });
    }

    const team = await Team.findOne({ inviteCode: inviteCode.toUpperCase() });
    if (!team) return res.status(404).json({ message: 'Invalid invite code' });

    if (team.members.includes(req.user._id)) {
      return res.status(400).json({ message: 'You are already a member of this team' });
    }

    team.members.push(req.user._id);
    await team.save();

    await User.findByIdAndUpdate(req.user._id, {
      teamId: team._id,
      role: 'member',
    });

    res.json(team);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// GET /api/teams/me - Get current user's team details
router.get('/me', protect, async (req, res) => {
  try {
    if (!req.user.teamId) {
      return res.status(404).json({ message: 'You are not in a team' });
    }

    const team = await Team.findById(req.user.teamId).populate(
      'members',
      'name email role'
    );
    if (!team) return res.status(404).json({ message: 'Team not found' });

    res.json(team);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// GET /api/teams/:id - Get team by ID
router.get('/:id', protect, async (req, res) => {
  try {
    const team = await Team.findById(req.params.id).populate(
      'members',
      'name email role'
    );
    if (!team) return res.status(404).json({ message: 'Team not found' });

    res.json(team);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// DELETE /api/teams/leave - Leave the team
router.delete('/leave', protect, async (req, res) => {
  try {
    if (!req.user.teamId) {
      return res.status(400).json({ message: 'You are not in a team' });
    }

    const team = await Team.findById(req.user.teamId);
    if (!team) return res.status(404).json({ message: 'Team not found' });

    if (team.leaderId.toString() === req.user._id.toString()) {
      return res.status(400).json({ message: 'Leader cannot leave. Transfer ownership or delete the team.' });
    }

    team.members = team.members.filter(
      (m) => m.toString() !== req.user._id.toString()
    );
    await team.save();

    await User.findByIdAndUpdate(req.user._id, { teamId: null, role: 'member' });

    res.json({ message: 'Left team successfully' });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

module.exports = router;
