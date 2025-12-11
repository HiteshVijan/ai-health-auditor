import { useState } from 'react';
import { Card, Button, Input } from '../components/common';

/**
 * User settings page.
 */
function SettingsPage() {
  const [fullName, setFullName] = useState('John Doe');
  const [email, setEmail] = useState('john@example.com');

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-2">Manage your account preferences</p>
      </div>

      <div className="max-w-2xl space-y-6">
        <Card title="Profile">
          <div className="space-y-4">
            <Input
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
            <Input
              type="email"
              label="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Button>Save Changes</Button>
          </div>
        </Card>

        <Card title="Password">
          <div className="space-y-4">
            <Input
              type="password"
              label="Current Password"
              placeholder="••••••••"
            />
            <Input
              type="password"
              label="New Password"
              placeholder="••••••••"
            />
            <Input
              type="password"
              label="Confirm New Password"
              placeholder="••••••••"
            />
            <Button>Update Password</Button>
          </div>
        </Card>

        <Card title="Notifications">
          <div className="space-y-4">
            <label className="flex items-center space-x-3">
              <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
              <span>Email notifications for completed audits</span>
            </label>
            <label className="flex items-center space-x-3">
              <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
              <span>Email notifications for negotiation updates</span>
            </label>
          </div>
        </Card>

        <Card title="Danger Zone">
          <p className="text-gray-600 mb-4">
            Once you delete your account, there is no going back.
          </p>
          <Button variant="danger">Delete Account</Button>
        </Card>
      </div>
    </div>
  );
}

export default SettingsPage;

