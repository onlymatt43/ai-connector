<?php
if (!defined('ABSPATH')) { exit; }

function heyhi_connector_get_options(){
  $opts = get_option(HEYHI_CONNECTOR_OPT_KEY);
  if (!$opts || !is_array($opts)) {
    $opts = array(
      'core_ai_base' => HEYHI_CORE_AI_BASE_DEFAULT,
      'api_key' => '',
      'allowed_origins' => 'https://onlymatt.ca,https://www.onlymatt.ca',
      'rate_limit_per_min' => 120,
      'debug' => 0
    );
  }
  return $opts;
}

function heyhi_connector_ensure_logs_dir(){
  $upload = wp_get_upload_dir();
  $dir = trailingslashit($upload['basedir']) . 'heyhi-logs';
  if (!file_exists($dir)) {
    wp_mkdir_p($dir);
  }
  return $dir;
}

function heyhi_connector_log($event, $data){
  $opts = heyhi_connector_get_options();
  if (empty($opts['debug'])) return;
  $dir = heyhi_connector_ensure_logs_dir();
  $file = trailingslashit($dir) . 'heyhi-' . date('Y-m-d') . '.log';
  $line = date('c') . ' ' . $event . ' ' . json_encode($data, JSON_UNESCAPED_UNICODE) . PHP_EOL;
  @file_put_contents($file, $line, FILE_APPEND);
}

function heyhi_connector_parse_origins($csv){
  $out = array();
  foreach (explode(',', (string)$csv) as $o) {
    $o = trim($o);
    if ($o) $out[] = $o;
  }
  return $out;
}

function heyhi_connector_apply_cors($req, $resp){
  $opts = heyhi_connector_get_options();
  $origins = heyhi_connector_parse_origins($opts['allowed_origins']);
  $origin = isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '';
  if ($origin && in_array($origin, $origins)) {
    $resp->header('Access-Control-Allow-Origin', $origin);
    $resp->header('Vary', 'Origin');
    $resp->header('Access-Control-Allow-Headers', 'Authorization, Content-Type, X-HeyHi-Key');
    $resp->header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
    $resp->header('Access-Control-Max-Age', '600');
  }
  return $resp;
}

function heyhi_connector_cors_preflight($req){
  $resp = new WP_REST_Response(array('ok'=>true));
  $resp->set_status(200);
  return heyhi_connector_apply_cors($req, $resp);
}

function heyhi_connector_authenticate($req, $opts){
  $hdr = isset($_SERVER['HTTP_X_HEYHI_KEY']) ? sanitize_text_field($_SERVER['HTTP_X_HEYHI_KEY']) : '';
  $key = isset($opts['api_key']) ? (string)$opts['api_key'] : '';
  if (!$key) return false;
  return hash_equals($key, $hdr);
}

// simple IP-based rate limit using transients
function heyhi_connector_rate_check($req, $opts){
  $limit = max(10, intval($opts['rate_limit_per_min']));
  $ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '0.0.0.0';
  $path = $req->get_route();
  $bucket = 'heyhi_rl_' . md5($ip . '|' . $path);
  $count = intval(get_transient($bucket));
  if ($count >= $limit) return false;
  $count++;
  // 60 seconds window
  set_transient($bucket, $count, 60);
  return true;
}

function heyhi_connector_json($arr){
  $resp = new WP_REST_Response($arr);
  $resp->set_status(200);
  // apply cors if any
  $req = new WP_REST_Request();
  return heyhi_connector_apply_cors($req, $resp);
}

function heyhi_connector_forward_json($url, $payload, $t_connect=10, $t_total=60){
  $args = array(
    'method' => 'POST',
    'headers' => array('Content-Type' => 'application/json'),
    'body' => wp_json_encode($payload),
    'timeout' => $t_total
  );
  $res = wp_remote_post($url, $args);
  if (is_wp_error($res)) {
    return array('error' => $res->get_error_message(), 'status'=>502, 'body'=>'');
  }
  $code = wp_remote_retrieve_response_code($res);
  $body = wp_remote_retrieve_body($res);
  return array('error'=>null, 'status'=>$code, 'body'=>$body);
}
