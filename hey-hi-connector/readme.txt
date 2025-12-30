=== Hey-Hi Connector ===
Contributors: onlymatt
Tags: api, ai, assistant, rest
Requires at least: 5.8
Tested up to: 6.6
Stable tag: 1.0.0
License: GPLv2 or later
License URI: http://www.gnu.org/licenses/gpl-2.0.html

Connecte WordPress à un Assistant IA (Render) via des endpoints REST sécurisés.

== Description ==
- Endpoints: /wp-json/heyhi/v1/health, /diag, /chat, /tools/run
- Sécurisé par clé `X-HeyHi-Key`
- CORS whitelist configurable
- Rate limit et logs (uploads/heyhi-logs)

== Installation ==
1. Téléverser le ZIP via Extensions → Ajouter.
2. Activer le plugin.
3. Réglages → Hey-Hi Connector: définir AI Base, API Key, Origins.
4. Tester: /wp-json/heyhi/v1/health

== Changelog ==
= 1.0.0 =
* Première version.
