---
name: assetcore-design
description: Use this skill to generate well-branded interfaces and assets for AssetCore (the medical-equipment lifecycle management platform built on ERPNext for hospitals — initially Bệnh Viện Nhi Đồng 1, delivered by Miyano), either for production or throwaway prototypes/mocks. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.

The UI is **Vietnamese-first**, hospital-domain, and formal-functional in tone. No emoji. No gradients except the login backdrop. Cool clinical blue (#2563eb) over white surfaces and slate text, with a near-black sidebar (#0f1623). Inter for body, Manrope for display, JetBrains Mono for IDs and codes — all from Google Fonts. The product is organised around 17 modules (IMM-01 → IMM-17) covering the WHO HTM lifecycle.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out of `assets/` and `ui_kits/` and create static HTML files for the user to view. Pull tokens from `colors_and_type.css`. For module navigation, follow the dark-sidebar pattern in `ui_kits/web/`.

If working on production code, the upstream is `mvl26/assetcore` on the `feature/hieuc/wave-2` branch — Vue 3 + TypeScript + Tailwind. The tokens in `colors_and_type.css` mirror that codebase's `frontend/src/assets/styles/main.css` and `tailwind.config.js`.

If the user invokes this skill without any other guidance, ask them what they want to build or design (a module screen? a launcher? a marketing surface?), ask some questions about role and module, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.
