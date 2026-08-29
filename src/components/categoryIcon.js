export function categoryIcon(category) {
  if (!category) return 'report_problem';
  const lower = category.toLowerCase();
  
  if (lower.includes('flood')) return 'flood';
  if (lower.includes('stp_') || lower.includes('sewage')) return 'water_pump';
  if (lower.includes('pump') || lower.includes('electrical')) return 'electrical_services';
  if (lower.includes('mosquito') || lower.includes('vector')) return 'pest_control';
  if (lower.includes('waste') || lower.includes('garbage')) return 'delete';
  if (lower.includes('water')) return 'water_drop';
  if (lower.includes('road') || lower.includes('pothole')) return 'construction';
  if (lower.includes('street_light')) return 'lightbulb';
  
  if (lower.includes('sanitation')) return 'delete';
  if (lower.includes('drainage')) return 'water_drop';
  if (lower.includes('electric')) return 'lightbulb';
  
  return 'report_problem';
}

export function titleCase(str) {
  if (!str) return '';
  return str.replace(/_/g, ' ').replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
}
