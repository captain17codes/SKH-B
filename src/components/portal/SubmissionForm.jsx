import React from 'react';
import Button from '../Button';
import CategorySelector from './CategorySelector';

export default function SubmissionForm() {
  return (
    <form className="flex flex-col gap-8">
      <CategorySelector />

      <div>
        <h3 className="text-xl font-bold text-on-surface mb-6">Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-bold font-label text-on-surface">Full Name</label>
            <input type="text" className="px-4 py-3 rounded-lg border border-surface-variant bg-surface text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" placeholder="Enter your name" />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-bold font-label text-on-surface">Phone Number</label>
            <input type="tel" className="px-4 py-3 rounded-lg border border-surface-variant bg-surface text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" placeholder="Enter phone number" />
          </div>
          <div className="flex flex-col gap-2 md:col-span-2">
            <label className="text-sm font-bold font-label text-on-surface">Description</label>
            <textarea rows="4" className="px-4 py-3 rounded-lg border border-surface-variant bg-surface text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" placeholder="Describe the issue..."></textarea>
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center pt-6 border-t border-surface-variant">
        <Button variant="ghost" type="button">Cancel</Button>
        <Button variant="primary" type="button">Next Step</Button>
      </div>
    </form>
  );
}
