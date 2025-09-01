const fs = require('fs');
const path = require('path');

// Function to fix absolute paths in HTML files
function fixPaths(directory) {
  const files = fs.readdirSync(directory);
  
  files.forEach(file => {
    const filePath = path.join(directory, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      fixPaths(filePath);
    } else if (file.endsWith('.html')) {
      console.log(`Fixing paths in: ${filePath}`);
      
      let content = fs.readFileSync(filePath, 'utf8');
      
      // Replace absolute paths with relative paths in HTML attributes
      content = content.replace(/href="\/_next\//g, 'href="./_next/');
      content = content.replace(/src="\/_next\//g, 'src="./_next/');
      
      // Also fix any other absolute paths
      content = content.replace(/href="\//g, 'href="./');
      content = content.replace(/src="\//g, 'src="./');
      
      // Fix absolute paths in JavaScript code embedded in HTML
      content = content.replace(/\/_next\//g, './_next/');
      
      // Fix specific patterns in the JavaScript code
      content = content.replace(/"href":\s*"\/_next\//g, '"href": "./_next/');
      content = content.replace(/"src":\s*"\/_next\//g, '"src": "./_next/');
      
      // Ensure all _next paths use ./_next/ (not ../_next/)
      content = content.replace(/href="\.\.\/_next\//g, 'href="./_next/');
      content = content.replace(/src="\.\.\/_next\//g, 'src="./_next/');
      
      fs.writeFileSync(filePath, content);
      console.log(`Fixed: ${filePath}`);
    }
  });
}

// Start fixing from the out directory
const outDir = path.join(__dirname, 'out');
if (fs.existsSync(outDir)) {
  console.log('Fixing absolute paths in built files...');
  fixPaths(outDir);
  console.log('Path fixing completed!');
} else {
  console.error('out directory not found. Please run npm run build first.');
}
