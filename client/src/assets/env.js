// Runtime config, loaded before the Angular bundle (see index.html).
//
// This file ships with a working dev default so `ng serve` / `npm start`
// need no extra setup. In the Docker image, a docker-entrypoint.d hook
// (client/docker-entrypoint.d/20-generate-env-js.sh) overwrites this file at
// container start from the GOOGLE_CLIENT_ID env var (itself sourced from the
// repo-root .env, see docker-compose.yml) -- so the value can be changed per
// environment without rebuilding the image.
window.__env = {
  GOOGLE_CLIENT_ID: '913568537440-clfeb4jvitdh7111s1j8cv6u8gb6t3dv.apps.googleusercontent.com'
};
