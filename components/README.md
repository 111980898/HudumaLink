# Visual component integration

`components.json` contains the React Bits Pro registries using the `REACTBITS_LICENSE_KEY` environment variable in the Authorization header. The requested install commands are:

```bash
npx shadcn@latest add @reactbits-starter/spectral-drape-tw
npx shadcn@latest add @reactbits-starter/vortex-tw
```

Huduma Link runs on Flask/Jinja, so the live homepage uses `hudumalink/static/js/spectral-drape.js` for the animated hero background and `hudumalink/static/js/vortex.js` for the scroll-reactive particle tunnel. `spectral-drape.tsx` and `vortex.tsx` provide matching React component APIs for future React surfaces.
