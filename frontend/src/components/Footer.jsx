import { APP_NAME } from './BrandMark.jsx';

export default function Footer() {
  return (
    <footer className="siteFooter hide-on-print">
      <p>
        &copy; {new Date().getFullYear()} {APP_NAME}. All rights are reserved.
      </p>
    </footer>
  );
}
