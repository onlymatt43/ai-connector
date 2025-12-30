<?php
if (!defined('ABSPATH')) { exit; }

/**
 * Handler pour /chat - Proxy vers Core AI
 */
function heyhi_connector_handle_chat($req) {
    $opts = heyhi_connector_get_options();
    
    // Vérification rate limit
    if (!heyhi_connector_rate_check($req, $opts)) {
        heyhi_connector_log('chat_rate_limit', array('ip' => $_SERVER['REMOTE_ADDR'] ?? 'unknown'));
        $resp = new WP_REST_Response(array(
            'error' => 'RATE_LIMIT_EXCEEDED',
            'message' => 'Trop de requêtes, réessayez dans 1 minute'
        ));
        $resp->set_status(429);
        return heyhi_connector_apply_cors($req, $resp);
    }
    
    // Authentification (optionnelle selon config)
    if (!empty($opts['api_key'])) {
        if (!heyhi_connector_authenticate($req, $opts)) {
            heyhi_connector_log('chat_auth_fail', array('ip' => $_SERVER['REMOTE_ADDR'] ?? 'unknown'));
            $resp = new WP_REST_Response(array(
                'error' => 'UNAUTHORIZED',
                'message' => 'Clé API invalide ou manquante'
            ));
            $resp->set_status(401);
            return heyhi_connector_apply_cors($req, $resp);
        }
    }
    
    // Récupération du body JSON
    $body = $req->get_json_params();
    if (!$body || !isset($body['messages'])) {
        $resp = new WP_REST_Response(array(
            'error' => 'BAD_REQUEST',
            'message' => 'Le champ "messages" est requis'
        ));
        $resp->set_status(400);
        return heyhi_connector_apply_cors($req, $resp);
    }
    
    // Validation basique
    if (!is_array($body['messages']) || count($body['messages']) === 0) {
        $resp = new WP_REST_Response(array(
            'error' => 'BAD_REQUEST',
            'message' => 'Le tableau "messages" doit contenir au moins un message'
        ));
        $resp->set_status(400);
        return heyhi_connector_apply_cors($req, $resp);
    }
    
    // Log de la requête (si debug activé)
    heyhi_connector_log('chat_request', array(
        'message_count' => count($body['messages']),
        'model' => $body['model'] ?? 'default',
        'session_id' => $body['session_id'] ?? null
    ));
    
    // Forward vers Core AI
    $core_url = trailingslashit($opts['core_ai_base']) . 'assistant/chat';
    $result = heyhi_connector_forward_json($core_url, $body, 10, 70);
    
    if ($result['error']) {
        heyhi_connector_log('chat_upstream_error', array(
            'error' => $result['error'],
            'url' => $core_url
        ));
        $resp = new WP_REST_Response(array(
            'error' => 'UPSTREAM_ERROR',
            'message' => 'Erreur lors de la communication avec le service IA',
            'detail' => $result['error']
        ));
        $resp->set_status(502);
        return heyhi_connector_apply_cors($req, $resp);
    }
    
    // Log de la réponse
    heyhi_connector_log('chat_response', array(
        'status' => $result['status'],
        'body_length' => strlen($result['body'])
    ));
    
    // Retourner la réponse du Core AI
    $data = json_decode($result['body'], true);
    if (!$data) {
        $data = array('error' => 'INVALID_RESPONSE', 'raw' => substr($result['body'], 0, 500));
    }
    
    $resp = new WP_REST_Response($data);
    $resp->set_status($result['status']);
    return heyhi_connector_apply_cors($req, $resp);
}

/**
 * Handler pour /tools - Gestion des outils WordPress
 */
function heyhi_connector_handle_tools($req) {
    $opts = heyhi_connector_get_options();
    
    // Vérification rate limit
    if (!heyhi_connector_rate_check($req, $opts)) {
        $resp = new WP_REST_Response(array(
            'error' => 'RATE_LIMIT_EXCEEDED',
            'message' => 'Trop de requêtes'
        ));
        $resp->set_status(429);
        return heyhi_connector_apply_cors($req, $resp);
    }
    
    // Authentification requise pour les tools
    if (!heyhi_connector_authenticate($req, $opts)) {
        $resp = new WP_REST_Response(array(
            'error' => 'UNAUTHORIZED',
            'message' => 'Authentification requise'
        ));
        $resp->set_status(401);
        return heyhi_connector_apply_cors($req, $resp);
    }
    
    $body = $req->get_json_params();
    $action = $body['action'] ?? '';
    
    heyhi_connector_log('tools_request', array('action' => $action));
    
    $result = array();
    
    switch ($action) {
        case 'get_posts':
            // Récupérer des posts WordPress
            $args = array(
                'post_type' => $body['post_type'] ?? 'post',
                'posts_per_page' => min(intval($body['limit'] ?? 10), 50),
                'post_status' => 'publish'
            );
            $posts = get_posts($args);
            $result = array_map(function($p) {
                return array(
                    'id' => $p->ID,
                    'title' => $p->post_title,
                    'excerpt' => wp_trim_words($p->post_content, 50),
                    'url' => get_permalink($p->ID),
                    'date' => $p->post_date
                );
            }, $posts);
            break;
            
        case 'search_content':
            // Recherche dans le contenu
            $search = sanitize_text_field($body['query'] ?? '');
            if ($search) {
                $query = new WP_Query(array(
                    's' => $search,
                    'posts_per_page' => 10,
                    'post_status' => 'publish'
                ));
                $result = array_map(function($p) {
                    return array(
                        'id' => $p->ID,
                        'title' => $p->post_title,
                        'excerpt' => get_the_excerpt($p),
                        'url' => get_permalink($p->ID)
                    );
                }, $query->posts);
            }
            break;
            
        case 'get_user_info':
            // Infos utilisateur courant
            $user = wp_get_current_user();
            if ($user->ID) {
                $result = array(
                    'id' => $user->ID,
                    'name' => $user->display_name,
                    'email' => $user->user_email,
                    'roles' => $user->roles
                );
            }
            break;
            
        default:
            $resp = new WP_REST_Response(array(
                'error' => 'UNKNOWN_ACTION',
                'message' => "Action '$action' non reconnue"
            ));
            $resp->set_status(400);
            return heyhi_connector_apply_cors($req, $resp);
    }
    
    $resp = new WP_REST_Response(array(
        'action' => $action,
        'result' => $result
    ));
    $resp->set_status(200);
    return heyhi_connector_apply_cors($req, $resp);
}

