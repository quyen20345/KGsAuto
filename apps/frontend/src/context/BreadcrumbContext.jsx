import { createContext, useContext, useState } from 'react';

const BreadcrumbContext = createContext(null);

export const useBreadcrumb = () => {
  const context = useContext(BreadcrumbContext);
  if (!context) {
    throw new Error('useBreadcrumb must be used within a BreadcrumbProvider');
  }
  return context;
};

export function BreadcrumbProvider({ children }) {
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const [headerExtra, setHeaderExtra] = useState(null);

  return (
    <BreadcrumbContext.Provider value={{ breadcrumbs, setBreadcrumbs, headerExtra, setHeaderExtra }}>
      {children}
    </BreadcrumbContext.Provider>
  );
}
