/** Static Tailwind build (standalone CLI) replacing the runtime CDN script.
 * Regenerate from the repo root after changing classes in templates or JS
 * (content globs are cwd-relative):
 *   make css
 */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/*.js"],
  theme: {
    extend: {},
  },
  plugins: [],
};
