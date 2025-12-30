<?php
if (!defined('ABSPATH')) { exit; }

$opts = heyhi_connector_get_options();
$updated = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST' && check_admin_referer('heyhi_connector_save','heyhi_nonce')) {
  $opts['core_ai_base'] = esc_url_raw($_POST['core_ai_base'] ?? HEYHI_CORE_AI_BASE_DEFAULT);
  $opts['api_key'] = sanitize_text_field($_POST['api_key'] ?? '');
  $opts['allowed_origins'] = sanitize_text_field($_POST['allowed_origins'] ?? '');
  $opts['rate_limit_per_min'] = intval($_POST['rate_limit_per_min'] ?? 120);
  $opts['debug'] = isset($_POST['debug']) ? 1 : 0;
  update_option(HEYHI_CONNECTOR_OPT_KEY, $opts);
  $updated = true;
}

?>
<div class="wrap">
  <h1>Hey-Hi Connector</h1>
  <?php if ($updated): ?>
    <div class="updated notice"><p>Réglages enregistrés.</p></div>
  <?php endif; ?>
  <form method="post">
    <?php wp_nonce_field('heyhi_connector_save','heyhi_nonce'); ?>
    <table class="form-table" role="presentation">
      <tr>
        <th scope="row"><label for="core_ai_base">Core AI Base URL</label></th>
        <td>
          <input name="core_ai_base" id="core_ai_base" type="url" class="regular-text" 
                 value="<?php echo esc_attr($opts['core_ai_base'] ?: HEYHI_CORE_AI_BASE_DEFAULT); ?>" />
          <p class="description">Ex: https://hey-hi-assistant-core-onlymatt.onrender.com ou https://ai.onlymatt.ca</p>
        </td>
      </tr>
      <tr>
        <th scope="row"><label for="api_key">WP API Key</label></th>
        <td>
          <input name="api_key" id="api_key" type="text" class="regular-text" value="<?php echo esc_attr($opts['api_key']); ?>" />
          <p class="description">Clé utilisée pour sécuriser les appels (header: X-HeyHi-Key).</p>
        </td>
      </tr>
      <tr>
        <th scope="row"><label for="allowed_origins">Allowed Origins (CORS)</label></th>
        <td>
          <input name="allowed_origins" id="allowed_origins" type="text" class="regular-text" 
                 value="<?php echo esc_attr($opts['allowed_origins']); ?>" />
          <p class="description">Ex: https://onlymatt.ca,https://www.onlymatt.ca,https://video.onlymatt.ca</p>
        </td>
      </tr>
      <tr>
        <th scope="row"><label for="rate_limit_per_min">Rate Limit / minute</label></th>
        <td>
          <input name="rate_limit_per_min" id="rate_limit_per_min" type="number" min="10" max="600" value="<?php echo intval($opts['rate_limit_per_min']); ?>" />
        </td>
      </tr>
      <tr>
        <th scope="row"><label for="debug">Debug logs</label></th>
        <td>
          <label><input type="checkbox" name="debug" id="debug" <?php checked(!empty($opts['debug'])); ?> /> Activer les logs détaillés</label>
        </td>
      </tr>
    </table>
    <p><button class="button button-primary" type="submit">Enregistrer</button></p>
  </form>
  <hr/>
  <h2>Diagnostics rapides</h2>
  <ul>
    <li><a href="<?php echo esc_url( rest_url('heyhi/v1/health') ); ?>" target="_blank">/wp-json/heyhi/v1/health</a></li>
    <li><a href="<?php echo esc_url( rest_url('heyhi/v1/diag') ); ?>" target="_blank">/wp-json/heyhi/v1/diag</a></li>
  </ul>
</div>
