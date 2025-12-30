<?php
/**
 * Plugin Name: Hey-Hi Connector
 * Description: Connecte WordPress à l’Assistant Core (Render) avec endpoints REST sécurisés (health, diag, chat, tools) + CORS + rate limit + logs.
 * Version: 1.0.0
 * Author: OnlyMatt
 * License: GPL-2.0+
 * Text Domain: heyhi-connector
 */

if (!defined('ABSPATH')) { exit; }

define('HEYHI_CONNECTOR_VERSION', '1.0.0');
define('HEYHI_CONNECTOR_SLUG', 'heyhi-connector');
define('HEYHI_CONNECTOR_OPT_GROUP', 'heyhi_connector_options');
define('HEYHI_CONNECTOR_OPT_KEY', 'heyhi_connector_settings');

// Defaults (you can change CORE_AI_BASE later in WP admin)
if (!defined('HEYHI_CORE_AI_BASE_DEFAULT')) {
  define('HEYHI_CORE_AI_BASE_DEFAULT', 'https://hey-hi-assistant-core-onlymatt.onrender.com');
}

require_once plugin_dir_path(__FILE__) . 'includes/utils.php';
require_once plugin_dir_path(__FILE__) . 'includes/request-handler.php';

/**
 * Activation: ensure logs dir exists
 */
register_activation_hook(__FILE__, function(){
  heyhi_connector_ensure_logs_dir();
  // Initialize options if missing
  $opts = get_option(HEYHI_CONNECTOR_OPT_KEY);
  if (!$opts || !is_array($opts)) {
    $opts = array(
      'core_ai_base' => HEYHI_CORE_AI_BASE_DEFAULT,
      'api_key' => '',
      'allowed_origins' => 'https://onlymatt.ca,https://www.onlymatt.ca',
      'rate_limit_per_min' => 120,
      'debug' => 0
    );
    add_option(HEYHI_CONNECTOR_OPT_KEY, $opts);
  }
});

/**
 * Admin: settings page
 */
add_action('admin_menu', function(){
  add_menu_page(
    __('Hey-Hi Connector','heyhi-connector'),
    'Hey-Hi Connector',
    'manage_options',
    HEYHI_CONNECTOR_SLUG,
    function(){
      require plugin_dir_path(__FILE__) . 'admin/settings-page.php';
    },
    'dashicons-rest-api',
    81
  );
});

/**
 * Register REST routes
 */
add_action('rest_api_init', function(){
  $ns = 'heyhi/v1';

  register_rest_route($ns, '/health', array(
    'methods' => 'GET',
    'callback' => function($req){
      return heyhi_connector_json(array('status'=>'ok','version'=>HEYHI_CONNECTOR_VERSION));
    },
    'permission_callback' => '__return_true'
  ));

  register_rest_route($ns, '/diag', array(
    'methods' => 'GET',
    'callback' => function($req){
      $opts = heyhi_connector_get_options();
      $pub = array(
        'status' => 'ok',
        'core_ai_base' => $opts['core_ai_base'],
        'has_api_key' => !!$opts['api_key'],
        'allowed_origins' => heyhi_connector_parse_origins($opts['allowed_origins']),
        'rate_limit_per_min' => intval($opts['rate_limit_per_min']),
        'debug' => !!$opts['debug']
      );
      return heyhi_connector_json($pub);
    },
    'permission_callback' => '__return_true'
  ));

  // Chat proxy -> Core /assistant/chat
  register_rest_route($ns, '/chat', array(
    'methods' => array('POST', 'OPTIONS'),
    'callback' => function($req){
      if ($req->get_method() === 'OPTIONS') {
        return heyhi_connector_cors_preflight($req);
      }
      return heyhi_connector_handle_chat($req);
    },
    'permission_callback' => '__return_true'
  ));

  // Tools WordPress natifs
  register_rest_route($ns, '/tools', array(
    'methods' => array('POST','OPTIONS'),
    'callback' => function($req){
      if ($req->get_method() === 'OPTIONS') {
        return heyhi_connector_cors_preflight($req);
      }
      return heyhi_connector_handle_tools($req);
    },
    'permission_callback' => '__return_true'
  ));

  // Tools passthrough -> Core /assistant/tools/run
  register_rest_route($ns, '/tools/run', array(
    'methods' => array('POST','OPTIONS'),
    'callback' => function($req){
      if ($req->get_method() === 'OPTIONS') {
        return heyhi_connector_cors_preflight($req);
      }
      $opts = heyhi_connector_get_options();
      $ok = heyhi_connector_authenticate($req, $opts);
      if (!$ok) {
        return new WP_REST_Response(array('error'=>'UNAUTHORIZED'), 401);
      }
      if (!heyhi_connector_rate_check($req, $opts)) {
        return new WP_REST_Response(array('error'=>'RATE_LIMIT'), 429);
      }
      $body = json_decode($req->get_body(), true);
      if (!is_array($body)) { $body = array(); }
      $core = rtrim($opts['core_ai_base'], '/');
      $url = $core . '/assistant/tools/run';
      $res = heyhi_connector_forward_json($url, $body, 15, 70);
      if ($res['error']) {
        heyhi_connector_log('tools_error', $res);
        return new WP_REST_Response(array('error'=>'UPSTREAM_FAIL','detail'=>$res['error']), 502);
      }
      heyhi_connector_log('tools_ok', array('status'=>$res['status'], 'bytes'=>strlen($res['body'])));
      $resp = new WP_REST_Response(json_decode($res['body'], true));
      $resp->set_status($res['status']);
      heyhi_connector_apply_cors($req, $resp);
      return $resp;
    },
    'permission_callback' => '__return_true'
  ));
});
