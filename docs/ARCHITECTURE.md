# Architecture

The app is an offline, dependency-free runtime written in JavaScript and CSS, bundled by Vite. Vanilla DOM rendering fits the small finite screen set and avoids runtime framework weight. All assets are local. Dev dependencies are pinned and locked.

Screens: home → setup → play → check → celebrate. Help returns safely; leaving play cancels animation. `requestAnimationFrame` advances elapsed seconds, capped per frame to prevent time jumps after suspension. Backgrounding or native Activity pause freezes play. Each challenge has three cues at 0/10/20 seconds and a 30-second endpoint. Only pressing “We joined in” updates completion. There is no inferred success.

Directional focus uses button centers, rejects candidates opposite the input, and scores forward distance plus perpendicular distance. Focus is set to a relevant main action after screen changes. Native Java translates key codes into the same JS handlers. Browser pointer clicks exercise identical actions.

`localStorage` key `togethermove.v1` holds `{completed: string[], sessions: number}` only. The normalizer deduplicates, filters unknown challenge identifiers, and rejects negative/noninteger session counts. Failed storage does not prevent gameplay and is disclosed on celebration.

The Fire OS host intercepts HTTPS requests for a single local origin and serves packaged assets. External navigation is blocked and no INTERNET permission is requested. Camera/microphone are absent. HTML, JavaScript and CSS never contain personal records.

## Design system

Midnight forest #09241f, warm cream #fff3d9, lime #d6fb79; coral, gold, lavender identify the moments. Large rounded native system typography, generous five-percent horizontal TV margins, visible cream focus outline, pill primary actions. Original botanical image is decorative; content and interaction remain native HTML. Reduced-motion preference disables animation.
