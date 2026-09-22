export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-gray-200 bg-white px-6 py-4">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-400">
        <span>
          © {year} Synchrony Financial. All rights reserved. &nbsp;·&nbsp;
          <span className="font-medium text-synchrony-navy">Synchrony Analytics Platform</span>
        </span>
        <span className="flex items-center gap-4">
          <a href="#" className="hover:text-synchrony-navy transition-colors">Privacy Policy</a>
          <a href="#" className="hover:text-synchrony-navy transition-colors">Terms of Use</a>
          <a href="#" className="hover:text-synchrony-navy transition-colors">Security</a>
        </span>
      </div>
    </footer>
  );
}
