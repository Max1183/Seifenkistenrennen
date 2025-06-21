import { useState, useEffect } from 'react';

function useSessionState<T>(key: string, initialValue: T): [T, React.Dispatch<React.SetStateAction<T>>] {
  // Holt den Wert aus dem sessionStorage oder nutzt den Initialwert
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.sessionStorage.getItem(key);
      // Parse stored json or if none return initialValue
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      // Bei Fehlern den Initialwert zurückgeben
      console.error(error);
      return initialValue;
    }
  });

  // useEffect, um den sessionStorage zu aktualisieren, wenn sich der State ändert
  useEffect(() => {
    try {
      window.sessionStorage.setItem(key, JSON.stringify(storedValue));
    } catch (error) {
      console.error(error);
    }
  }, [key, storedValue]);

  return [storedValue, setStoredValue];
}

export default useSessionState;