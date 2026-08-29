/**
 * Ticket Submission Form Component - Block 2 (Assistant 1)
 * Citizens submit grievances via this form
 */
import React, { useState, useRef } from 'react';
import { ticketsAPI } from '../api/client';

const CATEGORIES = [
  { value: 'pothole', label: 'Pothole/Road Damage', icon: '🕳️' },
  { value: 'waterlogging', label: 'Waterlogging/Flooding', icon: '💧' },
  { value: 'sanitation', label: 'Sanitation Issue', icon: '🗑️' },
  { value: 'water_quality', label: 'Water Quality', icon: '💦' },
  { value: 'streetlight', label: 'Streetlight Issue', icon: '💡' },
  { value: 'garbage', label: 'Garbage Collection', icon: '🚛' },
  { value: 'infrastructure', label: 'Infrastructure', icon: '🏗️' },
  { value: 'other', label: 'Other', icon: '📋' },
];

const WARDS = [
  'Ward-1', 'Ward-2', 'Ward-3', 'Ward-4', 'Ward-5',
  'Ward-6', 'Ward-7', 'Ward-8', 'Ward-9', 'Ward-10',
];

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
        setLocation({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
          getting: false
        });
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

    // Validation
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
        message: result.message,
        isDuplicate: result.is_duplicate
      });

      // Reset form
      setFormData({
        citizen_phone: '',
        category: '',
        description: '',
        ward_id: '',
      });
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
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-2">Report Civic Issue</h2>
      <p className="text-gray-600 mb-6">Submit a grievance with photo. Our AI system will prioritize and schedule it.</p>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border-l-4 border-green-500 p-4 mb-6">
          <p className="text-green-700 font-medium">{success.message}</p>
          <p className="text-green-600 text-sm mt-1">
            Ticket ID: <code className="bg-green-100 px-2 py-1 rounded">{success.ticketId.substring(0, 8)}</code>
          </p>
          {success.isDuplicate && (
            <p className="text-amber-600 text-sm mt-2">
              Your issue was merged with a similar existing report.
            </p>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Phone Number */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Phone Number <span className="text-red-500">*</span>
          </label>
          <input
            type="tel"
            name="citizen_phone"
            value={formData.citizen_phone}
            onChange={handleInputChange}
            placeholder="+91 or local number"
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
          <p className="text-xs text-gray-500 mt-1">Used for WhatsApp updates</p>
        </div>

        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Issue Category <span className="text-red-500">*</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat.value}
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, category: cat.value }))}
                className={`flex items-center p-3 border rounded-lg text-left transition-colors ${
                  formData.category === cat.value
                    ? 'bg-blue-50 border-blue-500 text-blue-700'
                    : 'hover:bg-gray-50 border-gray-200'
                }`}
              >
                <span className="text-xl mr-2">{cat.icon}</span>
                <span className="text-sm">{cat.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Ward */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ward
          </label>
          <select
            name="ward_id"
            value={formData.ward_id}
            onChange={handleInputChange}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select Ward (optional)</option>
            {WARDS.map(ward => (
              <option key={ward} value={ward}>{ward}</option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            rows={3}
            placeholder="Describe the issue in detail..."
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Location */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Location
          </label>
          <button
            type="button"
            onClick={getLocation}
            disabled={location.getting}
            className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            {location.getting ? (
              <>
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                Getting location...
              </>
            ) : location.lat ? (
              <>
                <svg className="h-5 w-5 mr-2 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                </svg>
                Location captured ({location.lat.toFixed(4)}, {location.lon.toFixed(4)})
              </>
            ) : (
              <>
                <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                Get Current Location
              </>
            )}
          </button>
        </div>

        {/* Photo Upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Photo <span className="text-red-500">*</span>
          </label>
          <div
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              photoPreview ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            {photoPreview ? (
              <div className="relative inline-block">
                <img
                  src={photoPreview}
                  alt="Preview"
                  className="max-h-48 rounded-lg shadow-md"
                />
                <span className="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded">
                  Ready
                </span>
              </div>
            ) : (
              <>
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                <p className="mt-2 text-sm text-gray-600">Click to upload photo</p>
                <p className="text-xs text-gray-500">JPG, PNG up to 10MB</p>
              </>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handlePhotoChange}
              className="hidden"
            />
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              Submitting...
            </span>
          ) : (
            'Submit Report'
          )}
        </button>
      </form>
    </div>
  );
}
