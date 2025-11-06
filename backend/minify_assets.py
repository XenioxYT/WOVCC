#!/usr/bin/env python3
"""
Minify CSS and JavaScript files for production
"""

import os
import re
from pathlib import Path

def minify_css(content):
    """
    Basic CSS minification:
    - Remove comments
    - Remove whitespace
    - Remove unnecessary semicolons
    """
    # Remove comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove whitespace around special characters
    content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', content)
    
    # Remove trailing semicolons before }
    content = re.sub(r';\}', '}', content)
    
    # Remove multiple spaces
    content = re.sub(r'\s+', ' ', content)
    
    # Remove leading/trailing whitespace
    content = content.strip()
    
    return content

def minify_js(content):
    """
    Basic JavaScript minification:
    - Remove comments
    - Remove unnecessary whitespace
    """
    # Remove single-line comments (but preserve URLs like http://)
    content = re.sub(r'(?<!:)//.*?$', '', content, flags=re.MULTILINE)
    
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove multiple spaces (but preserve in strings)
    content = re.sub(r'  +', ' ', content)
    
    # Remove whitespace around operators and punctuation
    content = re.sub(r'\s*([{}[\]();,:])\s*', r'\1', content)
    
    # Remove leading/trailing whitespace per line
    content = '\n'.join(line.strip() for line in content.split('\n'))
    
    # Remove empty lines
    content = re.sub(r'\n+', '\n', content)
    
    return content.strip()

def process_file(filepath, minify_func):
    """Process a single file with the given minification function"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original = f.read()
        
        minified = minify_func(original)
        
        # Only save if there's a size reduction
        original_size = len(original)
        minified_size = len(minified)
        
        if minified_size < original_size:
            # Create .min version
            min_filepath = filepath.parent / f"{filepath.stem}.min{filepath.suffix}"
            
            with open(min_filepath, 'w', encoding='utf-8') as f:
                f.write(minified)
            
            savings = ((original_size - minified_size) / original_size) * 100
            
            print(f"✓ {filepath.name}")
            print(f"  Original: {original_size / 1024:.1f} KB")
            print(f"  Minified: {minified_size / 1024:.1f} KB")
            print(f"  Savings: {savings:.1f}%\n")
            
            return True
        else:
            print(f"⊘ {filepath.name} (no savings)\n")
            return False
            
    except Exception as e:
        print(f"✗ Error processing {filepath.name}: {e}\n")
        return False

def main():
    print("🔧 WOVCC Asset Minifier")
    print("Minifying CSS and JavaScript files...\n")
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    
    # Process CSS files
    css_dir = project_root / 'styles'
    print(f"Processing CSS files in: {css_dir}\n")
    print("=" * 60)
    
    css_files = list(css_dir.glob('*.css'))
    css_processed = 0
    
    for css_file in css_files:
        # Skip already minified files
        if '.min.' not in css_file.name:
            if process_file(css_file, minify_css):
                css_processed += 1
    
    print("=" * 60)
    print(f"\nCSS Summary:")
    print(f"  Processed: {css_processed}")
    print(f"  Total: {len(css_files)}\n")
    
    # Process JavaScript files
    js_dir = project_root / 'scripts'
    print(f"Processing JavaScript files in: {js_dir}\n")
    print("=" * 60)
    
    js_files = list(js_dir.glob('*.js'))
    js_processed = 0
    
    for js_file in js_files:
        # Skip already minified files
        if '.min.' not in js_file.name:
            if process_file(js_file, minify_js):
                js_processed += 1
    
    print("=" * 60)
    print(f"\nJavaScript Summary:")
    print(f"  Processed: {js_processed}")
    print(f"  Total: {len(js_files)}\n")
    
    print("✅ Asset minification complete!")
    print("\nNext steps:")
    print("1. Update HTML templates to use .min.css and .min.js files in production")
    print("2. Configure your web server to serve .min files with proper caching headers")
    print("3. Run this script before deploying to production")

if __name__ == '__main__':
    main()
