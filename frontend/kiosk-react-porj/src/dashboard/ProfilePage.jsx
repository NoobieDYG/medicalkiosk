import { useState } from 'react';
import { useAuth } from './AuthContext.jsx';
import { apiFetch } from './doctorApi.js';

export default function ProfilePage() {
  const { doctor, setDoctor } = useAuth();

  // ----- details form -----
  const [name, setName] = useState(doctor.name || '');
  const [phone, setPhone] = useState(doctor.phone || '');
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState({ type: '', text: '' });

  const profileDirty =
    name.trim() !== (doctor.name || '') || phone.trim() !== (doctor.phone || '');

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setProfileMsg({ type: '', text: '' });

    if (!name.trim()) {
      setProfileMsg({ type: 'error', text: 'Name cannot be empty.' });
      return;
    }

    setSavingProfile(true);
    try {
      const updated = await apiFetch('/doctor/me', {
        method: 'PATCH',
        body: { name: name.trim(), phone: phone.trim() },
      });
      setDoctor(updated);
      setName(updated.name || '');
      setPhone(updated.phone || '');
      setProfileMsg({ type: 'success', text: 'Profile updated.' });
    } catch (err) {
      setProfileMsg({ type: 'error', text: err.message });
    } finally {
      setSavingProfile(false);
    }
  };

  // ----- password form -----
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordMsg, setPasswordMsg] = useState({ type: '', text: '' });

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setPasswordMsg({ type: '', text: '' });

    if (newPassword.length < 8) {
      setPasswordMsg({ type: 'error', text: 'New password must be at least 8 characters.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordMsg({ type: 'error', text: 'New passwords do not match.' });
      return;
    }

    setSavingPassword(true);
    try {
      await apiFetch('/doctor/me/password', {
        method: 'POST',
        body: { old_password: oldPassword, new_password: newPassword },
      });
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordMsg({ type: 'success', text: 'Password changed.' });
    } catch (err) {
      setPasswordMsg({ type: 'error', text: err.message });
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <div className="dr-page">
      <h1 className="dr-page-title">Profile</h1>

      <div className="dr-profile">
        <section className="dr-card">
          <h2 className="dr-card-title">Your details</h2>

          <dl className="dr-detail-list">
            <div><dt>Email</dt><dd>{doctor.email || '—'}</dd></div>
            <div><dt>Department</dt><dd>{doctor.department || '—'}</dd></div>
          </dl>

          <form className="dr-form" onSubmit={handleProfileSubmit}>
            <label className="dr-label">
              Name
              <input
                className="dr-input"
                type="text"
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label className="dr-label">
              Phone
              <input
                className="dr-input"
                type="tel"
                maxLength={15}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </label>

            {profileMsg.text && (
              <p className={profileMsg.type === 'success' ? 'dr-success' : 'dr-error'}>
                {profileMsg.text}
              </p>
            )}

            <div className="dr-form-actions">
              <button
                type="submit"
                className="dr-btn dr-btn--primary"
                disabled={savingProfile || !profileDirty}
              >
                {savingProfile ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </form>
        </section>

        <section className="dr-card">
          <h2 className="dr-card-title">Change password</h2>

          <form className="dr-form" onSubmit={handlePasswordSubmit}>
            <label className="dr-label">
              Current password
              <input
                className="dr-input"
                type="password"
                maxLength={72}
                autoComplete="current-password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
              />
            </label>
            <label className="dr-label">
              New password
              <input
                className="dr-input"
                type="password"
                maxLength={72}
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </label>
            <label className="dr-label">
              Confirm new password
              <input
                className="dr-input"
                type="password"
                maxLength={72}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </label>

            {passwordMsg.text && (
              <p className={passwordMsg.type === 'success' ? 'dr-success' : 'dr-error'}>
                {passwordMsg.text}
              </p>
            )}

            <div className="dr-form-actions">
              <button type="submit" className="dr-btn dr-btn--primary" disabled={savingPassword}>
                {savingPassword ? 'Changing…' : 'Change password'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}