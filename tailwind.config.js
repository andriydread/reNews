/** Static Tailwind build (standalone CLI) replacing the runtime CDN script.
 * Regenerate after changing classes in templates or JS:
 *   tailwindcss -c tailwind.config.js -i static/css/tailwind.src.css -o static/css/tailwind.css --minify
 */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/*.js"],
  theme: {
    extend: {},
  },
  plugins: [],
};
