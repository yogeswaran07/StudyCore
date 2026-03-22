const mongoose = require('mongoose');

const taskSchema = new mongoose.Schema(
  {
    teamId: { type: mongoose.Schema.Types.ObjectId, ref: 'Team', required: true },
    title: { type: String, required: true, trim: true },
    description: { type: String, default: '' },
    order: { type: Number, required: true },
    completedBy: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
    status: { type: String, enum: ['locked', 'active', 'completed'], default: 'locked' },
  },
  { timestamps: true }
);

module.exports = mongoose.model('Task', taskSchema);
