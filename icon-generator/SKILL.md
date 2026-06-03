---
name: icon-generator
description: generate production-ready svg icons and framework components from natural-language icon requests. use when the user asks for an icon, svg icon, react icon component, vue icon component, icon set, frontend icon asset, or asks to convert/refine an icon between svg, react, or vue. default to react component output unless the user explicitly asks for plain svg only or vue output.
---

# Icon Generator

## Overview

Generate clean, production-ready icons as SVG and frontend components. Default to a React component plus the source SVG; produce Vue components when the user explicitly requests Vue.

## Default Output Decision

1. If the user asks for an icon without specifying a framework, output:
   - A React component first.
   - The equivalent raw SVG second.
2. If the user asks for SVG only, output only raw SVG.
3. If the user asks for Vue, output:
   - A Vue single-file component first.
   - The equivalent raw SVG second.
4. If the user asks for multiple icons, output one component/SVG pair per icon and keep names consistent.
5. If the user provides project conventions, follow them over these defaults.

## Icon Design Rules

Use these defaults unless the user specifies otherwise:

- Size: `24x24` with `viewBox="0 0 24 24"`.
- Color: `currentColor`; do not hard-code colors unless requested.
- Stroke icons: `fill="none"`, `stroke="currentColor"`, `strokeWidth={2}` in React, `stroke-width="2"` in SVG/Vue, `strokeLinecap="round"`, `strokeLinejoin="round"`.
- Filled icons: use `fill="currentColor"`; avoid strokes unless visually necessary.
- Accessibility: include `aria-hidden="true"` by default for decorative icons. If the user says the icon needs an accessible name, add `role="img"` and a `<title>`.
- Geometry: use simple paths, circles, lines, polylines, polygons, and rectangles. Avoid unnecessary groups, masks, filters, embedded raster images, and IDs.
- Maintainability: keep SVG compact but readable; avoid editor metadata, comments, inline styles, and `class` unless requested.
- Visual balance: center artwork in the 24x24 box with roughly 2px optical padding unless the icon intentionally reaches the edge.

## React Component Requirements

Default React output should be TypeScript-friendly and accept standard SVG props.

Use this shape:

```tsx
import type { SVGProps } from "react";

export function IconName(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={24}
      height={24}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {/* icon elements */}
    </svg>
  );
}
```

Rules:

- Use PascalCase component names, e.g. `SearchSparkIcon`.
- Convert SVG attributes to JSX attributes: `stroke-width` → `strokeWidth`, `stroke-linecap` → `strokeLinecap`, `fill-rule` → `fillRule`, `clip-rule` → `clipRule`, `class` → `className`.
- Put `{...props}` after default attributes so users can override them.
- Do not use `React.FC` unless the project specifically requests it.
- If exporting many icons, use named exports.

## Vue Component Requirements

When Vue is requested, output a Vue 3 single-file component by default.

Use this shape:

```vue
<script setup lang="ts">
defineOptions({ name: "IconName" });
</script>

<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- icon elements -->
  </svg>
</template>
```

Rules:

- Use PascalCase component names.
- Keep SVG attributes kebab-case in Vue templates.
- If the user requests prop-driven size/title, add `defineProps` and bind attributes with `:`.

## Raw SVG Requirements

Raw SVG output should be directly copy-pasteable.

Use this shape for stroke icons:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <!-- icon elements -->
</svg>
```

## Naming Rules

- Infer clear names from the request: `CloudUploadIcon`, `AiSparkIcon`, `UserShieldIcon`.
- For batches, keep names parallel: `HomeIcon`, `SearchIcon`, `SettingsIcon`.
- Avoid generic names like `Icon1` unless the user provides no semantic label.

## Quality Checklist

Before finalizing, check that:

- The icon fits the requested metaphor and style.
- The SVG is valid XML.
- React JSX compiles: attribute names are JSX-compatible, tags are closed, and braces are correct.
- Vue output uses valid template attributes.
- No hard-coded colors are present unless requested.
- `viewBox`, `width`, and `height` are present.
- The answer is not cluttered with implementation explanation unless the user asks for it.

## Optional Script

Use `scripts/icon_transform.py` when converting a saved SVG file to React or Vue or when validating generated SVG syntax. The script can:

- Validate that raw SVG parses as XML.
- Convert common SVG attributes to JSX for React.
- Wrap SVG content into React or Vue component templates.

Examples:

```bash
python scripts/icon_transform.py input.svg --name CloudUploadIcon --format react
python scripts/icon_transform.py input.svg --name CloudUploadIcon --format vue
python scripts/icon_transform.py input.svg --validate-only
```
