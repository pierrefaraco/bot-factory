const fs = require('fs');
const path = require('path');

function optimizeAssets() {
  const distPath = path.join(__dirname, 'dist', 'alfred_react');
  
  if (!fs.existsSync(distPath)) {
    console.log('Build directory not found. Run ng build first.');
    return;
  }

  // Add compression headers suggestion
  const htaccessContent = `
# Enable Gzip compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/plain
    AddOutputFilterByType DEFLATE text/html
    AddOutputFilterByType DEFLATE text/xml
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/xml
    AddOutputFilterByType DEFLATE application/xhtml+xml
    AddOutputFilterByType DEFLATE application/rss+xml
    AddOutputFilterByType DEFLATE application/javascript
    AddOutputFilterByType DEFLATE application/x-javascript
</IfModule>

# Set cache headers
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/jpg "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
    ExpiresByType image/svg+xml "access plus 1 year"
    ExpiresByType application/pdf "access plus 1 month"
    ExpiresByType text/html "access plus 0 seconds"
</IfModule>
`;

  fs.writeFileSync(path.join(distPath, '.htaccess'), htaccessContent);
  console.log('✅ Created .htaccess with compression and caching rules');
  
  console.log('✅ Build optimization completed');
}

if (require.main === module) {
  optimizeAssets();
}

module.exports = { optimizeAssets };