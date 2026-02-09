/**
 * Date utility functions for handling timezone-safe date operations
 * 
 * Backend returns dates as "YYYY-MM-DDTHH:mm:ss" (naive datetime)
 * These utils ensure consistent parsing and formatting in local timezone
 */

/**
 * Parse date string from backend (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss)
 * Returns a Date object at midnight LOCAL time
 * 
 * @param dateString - Date string from backend
 * @returns Date object in local timezone or null
 */
export const parseDateSafe = (dateString: string | null | undefined): Date | null => {
    if (!dateString) return null;
    
    // Extract just the date part (YYYY-MM-DD)
    const datePart = dateString.split('T')[0];
    const [year, month, day] = datePart.split('-').map(Number);
    
    // Create date in LOCAL timezone (not UTC)
    // Month is 0-indexed in JavaScript Date
    return new Date(year, month - 1, day);
  };
  
  /**
   * Format Date object to YYYY-MM-DD string (for backend API)
   * Uses local timezone, no UTC conversion
   * 
   * @param date - Date object to format
   * @returns YYYY-MM-DD string or empty string
   */
  export const formatDateToYYYYMMDD = (date: Date | null | undefined): string => {
    if (!date) return '';
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
  };
  
  /**
   * Format date string for display (short format)
   * Example: "Mar 19, 2026"
   * 
   * @param dateString - Date string from backend
   * @returns Formatted date string or 'N/A'
   */
  export const formatDateForDisplay = (dateString: string | null | undefined): string => {
    if (!dateString) return 'N/A';
    
    const date = parseDateSafe(dateString);
    if (!date) return 'N/A';
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };
  
  /**
   * Format date string for display (long format)
   * Example: "Thursday, March 19, 2026"
   * 
   * @param dateString - Date string from backend
   * @returns Formatted date string or 'N/A'
   */
  export const formatDateForDisplayLong = (dateString: string | null | undefined): string => {
    if (!dateString) return 'N/A';
    
    const date = parseDateSafe(dateString);
    if (!date) return 'N/A';
    
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };
  