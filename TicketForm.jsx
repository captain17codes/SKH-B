/**
 * Ticket Submission Form Component
 * Citizens submit grievances via this form. Categories and wards are pulled live
 * from the reference API so an unrecognised category never silently scores as
 * "unclassified".
 */
import React, { useState, useRef, useEffect } from 'react';
import { ticketsAPI, referenceAPI } from '../api/client';
import { categoryIcon, titleCase } from './categoryIcon';

export default function TicketForm({ onSuccess }) {
  const [formData, setFormData] = useState({
    citizen_phone: '',
    category: '',
    description: '',
    ward_id: '',
  });
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [location, setLocation] = useState({ lat: null, lon: null, getting: false });
  const fileInputRef = useRef(null);

  const [categories, setCategories] = useState([]);
  const [wards, setWards] = useState([]);
  const [refLoading, setRefLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      referenceAPI.categories(false).catch(() => ({ categories: [] })),
      ticketsAPI.wards().catch(() => ({ wards: [] })),
    ]).then(([catRes, wardRes]) => {
      if (!mounted) return;
      setCategories(catRes.categories || []);
      setWards(wardRes.wards || []);
      setRefLoading(false);
    });
    return () => { mounted = false; };
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        setError('File too large. Max size is 10MB.');
        return;
      }
      setPhoto(file);
      setPhotoPreview(URL.createObjectURL(file));
      setError(null);
    }
  };

  const getLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by this browser.');
      return;
    }
    setLocation(prev => ({ ...prev, getting: true }));
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({ lat: position.coords.latitude, lon: position.coords.longitude, getting: false });
        setError(null);
      },
      (err) => {
        setLocation({ lat: null, lon: null, getting: false });
        setError(`Location error: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    if (!formData.citizen_phone.match(/^\+?[0-9]{10,15}$/)) {
      setError('Please enter a valid phone number (10-15 digits)');
      setLoading(false);
      return;
    }
    if (!formData.category) {
      setError('Please select a category');
      setLoading(false);
      return;
    }
    if (!photo) {
      setError('Please upload a photo of the issue');
      setLoading(false);
      return;
    }

    try {
      const submitData = new FormData();
      submitData.append('citizen_phone', formData.citizen_phone);
      submitData.append('category', formData.category);
      submitData.append('description', formData.description);
      submitData.append('ward_id', formData.ward_id);
      if (location.lat) submitData.append('lat', location.lat);
      if (location.lon) submitData.append('lon', location.lon);
      submitData.append('file', photo);

      const result = await ticketsAPI.submit(submitData);

      setSuccess({
        ticketId: result.id,
        refNo: result.ref_no || result.id.substring(0, 8),
        message: result.message,
        isDuplicate: result.is_duplicate,
        fullResult: result
      });

      setFormData({ citizen_phone: '', category: '', description: '', ward_id: '' });
      setPhoto(null);
      setPhotoPreview(null);
      setLocation({ lat: null, lon: null, getting: false });

      if (onSuccess) onSuccess(result);
    } catch (err) {
      setError(err.message || 'Failed to submit ticket. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/20 p-6 md:p-8">
      <h2 className="font-headline-md text-headline-md text-primary mb-2">Report a Civic Issue</h2>
      <p className="font-body-md text-body-md text-on-surface-variant mb-6">Submit a grievance with a photo. Our AI system prioritises and schedules it automatically.</p>

      {error && (
        <div className="bg-error-container text-on-error-container p-4 mb-6 rounded-lg flex items-start gap-2">
          <span className="material-symbols-outlined text-[20px] mt-0.5">error</span>
          <p>{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-tertiary-fixed/30 border border-tertiary-fixed p-4 mb-6 rounded-lg">
          <p className="text-on-surface font-semibold flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">check_circle</span>
            {success.message}
          </p>
          <p className="text-on-surface-variant text-sm mt-1 mb-3">
            Reference No: <code className="bg-surface-container-high px-2 py-1 rounded font-mono">{success.refNo}</code>
          </p>
          {success.isDuplicate && (
            <p className="text-[#9a6a16] text-sm mt-2 mb-3">
              Your issue was merged with a similar existing report for faster resolution.
            </p>
          )}
          <button
            type="button"
            onClick={() => onSuccess && onSuccess(success.fullResult)}
            className="mt-2 bg-primary hover:bg-primary-container text-on-primary py-2 px-4 rounded-full font-label-sm text-label-sm font-bold transition-colors inline-flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">psychology</span>
            View AI Explanation
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Phone Number */}
        <div>
          <label className="block font-label-sm text-label-sm text-on-surface mb-1">
            Phone Number <span className="text-error">*</span>
          </label>
          <input
            type="tel"
            name="citizen_phone"
            value={formData.citizen_phone}
            onChange={handleInputChange}
            placeholder="+91 or local number"
            className="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed/50 transition-all"
            required
          />
          <p className="text-xs text-on-surface-variant mt-1">Used for status updates.</p>
        </div>

        {/* Category */}
        <div>
          <label className="block font-label-sm text-label-sm text-on-surface mb-2">
            Issue Category <span className="text-error">*</span>
          </label>
          {refLoading ? (
            <div className="grid grid-cols-2 gap-2 animate-pulse">
              {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-12 bg-surface-container rounded-lg" />)}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
              {categories.map(cat => (
                <button
                  key={cat.incident_type}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, category: cat.incident_type }))}
                  title={cat.department_name}
                  className={`flex items-center gap-2 p-3 border rounded-lg text-left transition-colors ${
                    formData.category === cat.incident_type
                      ? 'bg-primary-container text-on-primary-container border-primary'
                      : 'hover:bg-surface-container-low border-outline-variant/40 text-on-surface'
                  }`}
                >
                  <span className="material-symbols-outlined text-[20px] shrink-0">{categoryIcon(cat.incident_type)}</span>
                  <span className="text-sm truncate">{titleCase(cat.incident_type)}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Ward */}
        <div>
          <label className="block font-label-sm text-label-sm text-on-surface mb-1">Ward</label>
          <select
            name="ward_id"
            value={formData.ward_id}
            onChange={handleInputChange}
            className="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed/50 transition-all"
          >
            <option value="">Select ward (optional)</option>
            {wards.map(w => (
              <option key={w.id} value={w.id}>{w.name || w.id}</option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="block font-label-sm text-label-sm text-on-surface mb-1">Description</label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            rows={3}
            placeholder="Describe the issue in detail..."
            className="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed/50 transition-all"
          />
        </div>

        {/* Location */}
        <div>
          <label className="block font-label-sm text-label-sm text-on-surface mb-2">Location</label>
          <button
            type="button"
            onClick={getLocation}
            disabled={location.getting}
            className="flex items-center px-4 py-2.5 bg-surface-container-low text-on-surface rounded-lg hover:bg-surface-container transition-colors border border-outline-variant/30"
          >
            <span className={`material-symbols-outlined mr-2 ${location.getting ? 'animate-spin' : ''} ${location.lat ? 'text-primary' : ''}`}>
              {location.getting ? 'progress_activity' : location.lat ? 'check_circle' : 'my_location'}
            </span>
            {location.getting ? 'Getting location...' : location.lat ? `Location captured (${location.lat.toFixed(4)}, ${location.lon.toFixed(4)})` : 'Get Current Location'}
          </button>
        </div>

        {/* Photo Upload */}
        <div>
          <label className="block font-label-sm text-label-sm text-on-surface mb-2">
            Photo <span className="text-error">*</span>
          </label>
          <div
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              photoPreview ? 'border-primary bg-primary/5' : 'border-outline-variant hover:border-primary/60'
            }`}
          >
            {photoPreview ? (
              <div className="relative inline-block">
                <img src={photoPreview} alt="Preview" className="max-h-48 rounded-lg shadow-md" />
                <span className="absolute top-2 right-2 bg-primary text-on-primary text-xs px-2 py-1 rounded-full">Ready</span>
              </div>
            ) : (
              <>
                <span className="material-symbols-outlined text-4xl text-outline">add_a_photo</span>
                <p className="mt-2 text-sm text-on-surface-variant">Click to upload photo</p>
                <p className="text-xs text-outline">JPG, PNG up to 10MB</p>
              </>
            )}
            <input ref={fileInputRef} type="file" accept="image/*" onChange={handlePhotoChange} className="hidden" />
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-on-primary py-3.5 px-6 rounded-full font-label-sm text-label-sm font-bold hover:bg-primary-container transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="material-symbols-outlined animate-spin">progress_activity</span>
              Submitting...
            </>
          ) : 'Submit Report'}
        </button>
      </form>
    </div>
  );
}
