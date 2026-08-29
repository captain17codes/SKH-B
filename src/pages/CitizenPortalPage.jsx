import React, { useState, useRef } from 'react';
import { ticketsAPI } from '../api/client';

export default function CitizenPortalPage() {
  const [formData, setFormData] = useState({ category: '', description: '', citizen_phone: '' });
  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [location, setLocation] = useState({ lat: null, lon: null });
  const [locationCaptured, setLocationCaptured] = useState(false);
  const [locating, setLocating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successData, setSuccessData] = useState(null);
  const fileInputRef = useRef(null);

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({ ...prev, [id]: value }));
  };

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f) {
      setFile(f);
      setFilePreview(URL.createObjectURL(f));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validate phone number
    const rawPhone = formData.citizen_phone;
    const strippedPhone = rawPhone.replace(/[\s\-().]/g, '');
    
    // a) exactly 10 digits, first digit 6-9
    const isLocal = /^[6-9]\d{9}$/.test(strippedPhone);
    // b) E.164-ish: optional +, 1-3 digit country code, 10 digits
    const isE164 = /^\+?\d{1,3}\d{10}$/.test(strippedPhone);

    if (!isLocal && !isE164) {
      setError("Enter a valid 10-digit phone number or include country code (e.g. +91 9876543210).");
      return;
    }

    if (!locationCaptured) {
      setError("Please capture your location before submitting.");
      return;
    }

    if (!file) {
      setError("Please attach a photo of the issue. A valid photo is required for processing.");
      return;
    }

    setLoading(true);

    try {
      const submitData = new FormData();
      submitData.append('citizen_phone', strippedPhone);
      submitData.append('category', formData.category);
      submitData.append('description', formData.description);
      submitData.append('lat', location.lat);
      submitData.append('lon', location.lon);
      submitData.append('file', file);

      const result = await ticketsAPI.submit(submitData);
      
      setSuccessData(result);
      setShowSuccess(true);
    } catch (err) {
      setError(err.message || "Could not submit ticket. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setShowSuccess(false);
    setSuccessData(null);
    setFormData({ category: '', description: '', citizen_phone: '' });
    setFile(null);
    setFilePreview(null);
    setLocationCaptured(false);
    setLocation({ lat: null, lon: null });
    setLocating(false);
    setError(null);
  };

  const captureLocation = () => {
    setLocating(true);
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by this browser.');
      setLocating(false);
      return;
    }
    
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lon: position.coords.longitude
        });
        setLocationCaptured(true);
        setLocating(false);
        setError(null);
      },
      (err) => {
        setLocating(false);
        setError(`Location error: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  };

  return (
    <div className="bg-surface text-on-surface font-body-md min-h-screen relative overflow-x-hidden">
      <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-12 md:py-24 relative z-10 flex justify-center min-h-screen items-center">
        <div className="w-full max-w-2xl rounded-xl p-6 md:p-10 shadow-lg animate-slide-up bg-surface-container border border-outline">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-primary text-on-primary rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="material-symbols-outlined text-[32px]" style={{fontVariationSettings: "'FILL' 1"}}>report</span>
            </div>
            <h1 className="text-headline-lg-mobile md:text-headline-lg font-headline-lg text-on-surface mb-2">Report a Civic Issue</h1>
            <p className="text-body-md font-body-md text-on-surface-variant">Your contribution helps keep Kopargaon clean, safe, and beautiful.</p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Phone Number */}
            <div>
              <label className="block text-label-sm font-label-sm text-on-surface mb-2" htmlFor="citizen_phone">Phone number</label>
              <input type="tel" id="citizen_phone" autoComplete="tel" inputMode="tel" value={formData.citizen_phone} onChange={handleInputChange} className="form-input-custom w-full bg-surface-container-lowest border border-outline text-body-md font-body-md rounded-lg py-3 px-4 text-on-surface transition-all duration-200" placeholder="+91 9876543210" required />
            </div>

            {/* Category Dropdown */}
            <div>
              <label className="block text-label-sm font-label-sm text-on-surface mb-2" htmlFor="category">Issue Category</label>
              <div className="relative">
                <select className="form-input-custom w-full appearance-none bg-surface-container-lowest border border-outline text-body-md font-body-md rounded-lg py-3 pl-4 pr-10 text-on-surface transition-all duration-200" id="category" value={formData.category} onChange={handleInputChange} required>
                  <option disabled value="">Select category...</option>
                  <option value="pothole">Pothole / Road Repair</option>
                  <option value="waterlogging">Waterlogging / Flooding</option>
                  <option value="sanitation">Sanitation Issue</option>
                  <option value="water_quality">Water Supply / Quality</option>
                  <option value="streetlight">Streetlight Issue</option>
                  <option value="garbage">Garbage / Waste Collection</option>
                  <option value="infrastructure">Infrastructure / Bridge</option>
                  <option value="other">Other Civic Issue</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-on-surface">
                  <span className="material-symbols-outlined">expand_more</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-label-sm font-label-sm text-on-surface mb-2" htmlFor="description">Detailed Description</label>
              <textarea className="form-input-custom w-full bg-surface-container-lowest border border-outline text-body-md font-body-md rounded-lg p-4 text-on-surface transition-all duration-200 resize-none" id="description" placeholder="Please provide specific details about the issue..." value={formData.description} onChange={handleInputChange} required rows="4"></textarea>
            </div>

            {/* Bento Grid for Media & Location */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="border border-outline bg-surface-container-low rounded-lg p-4 flex flex-col items-center justify-center min-h-[140px] border-dashed cursor-pointer hover:bg-surface-container-high transition-colors group relative overflow-hidden" onClick={() => fileInputRef.current?.click()}>
                <input accept="image/*" className="hidden" type="file" ref={fileInputRef} onChange={handleFileChange} />
                {filePreview ? (
                  <img src={filePreview} alt="Preview" className="w-full h-full object-cover absolute inset-0 z-0 opacity-50" />
                ) : null}
                <div className="relative z-10 flex flex-col items-center pointer-events-none">
                  <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary mb-2 transition-colors">add_a_photo</span>
                  <span className="text-label-sm font-label-sm text-on-surface text-center">Tap to attach a photo<br/><span className="text-primary font-bold text-xs">(Required)</span></span>
                </div>
              </div>
              <div className="border border-outline bg-surface-container-low rounded-lg p-4 flex flex-col justify-center items-start min-h-[140px] relative overflow-hidden group">
                <div className="relative z-10 w-full">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-primary" style={{fontVariationSettings: "'FILL' 1"}}>location_on</span>
                    <span className="text-label-sm font-label-sm text-on-surface font-bold">Location Data</span>
                  </div>
                  {locationCaptured ? (
                    <p className="text-[12px] font-body-md text-primary font-bold mb-3 leading-tight">Lat: {location.lat?.toFixed(4)}° N<br/>Lng: {location.lon?.toFixed(4)}° E</p>
                  ) : (
                    <p className="text-[12px] font-body-md text-on-surface-variant mb-3 leading-tight">Requires GPS access to accurately tag the issue location.</p>
                  )}
                  <button
                    className={`w-full py-2 px-4 border text-label-sm font-label-sm rounded-lg transition-colors flex items-center justify-center gap-2 ${locationCaptured ? 'bg-primary-container text-on-primary-container border-transparent' : 'border-primary bg-surface-container-lowest text-primary hover:bg-primary hover:text-on-primary'}`}
                    onClick={captureLocation}
                    type="button"
                    disabled={locating || locationCaptured}
                  >
                    {locating ? (
                      <><span className="material-symbols-outlined text-[18px] animate-spin">sync</span> Locating...</>
                    ) : locationCaptured ? (
                      <><span className="material-symbols-outlined text-[18px]" style={{fontVariationSettings: "'FILL' 1"}}>check</span> Location Captured</>
                    ) : (
                      <><span className="material-symbols-outlined text-[18px]">my_location</span> Capture Location</>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {error && (
              <div className="bg-error-container text-on-error-container p-4 rounded-lg text-sm font-bold mt-4">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <div className="pt-4 mt-8">
              <button disabled={loading} className="w-full bg-primary text-on-primary py-4 px-6 rounded-lg text-label-sm font-label-sm font-bold hover:bg-primary-container hover:text-on-primary-container disabled:opacity-50 transition-all duration-200 flex items-center justify-center gap-2" type="submit">
                {loading ? (
                  <><span className="material-symbols-outlined text-[20px] animate-spin">sync</span><span>Submitting...</span></>
                ) : (
                  <><span>Submit Issue Ticket</span><span className="material-symbols-outlined text-[20px]" style={{fontVariationSettings: "'FILL' 1"}}>send</span></>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Success Modal */}
      {showSuccess && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center px-margin-mobile bg-surface/90">
          <div className="w-full max-w-md rounded-xl p-8 text-center shadow-lg border border-outline-variant bg-surface-container-lowest">
            <div className="w-20 h-20 bg-primary-fixed text-on-primary-fixed rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="material-symbols-outlined text-[40px]" style={{fontVariationSettings: "'FILL' 1"}}>check_circle</span>
            </div>
            <h2 className="text-headline-md font-headline-md text-primary mb-2">Ticket Submitted</h2>
            <p className="text-body-md font-body-md text-on-surface-variant mb-6">Thank you. The relevant municipal department has been notified.</p>
            <div className="bg-surface-container-low rounded-lg p-4 mb-8 border border-outline-variant">
              <span className="block text-[12px] font-label-sm text-on-surface-variant uppercase tracking-wider mb-1">Reference Number</span>
              <span className="block text-headline-md font-headline-md text-primary tracking-widest font-mono">{successData?.id || 'KMC-9284-A'}</span>
            </div>
            <button className="w-full bg-primary-container text-on-primary-container border border-primary-container py-3 px-6 rounded-lg text-label-sm font-label-sm hover:bg-primary hover:text-on-primary transition-colors" onClick={resetForm}>
              Submit Another Issue
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
