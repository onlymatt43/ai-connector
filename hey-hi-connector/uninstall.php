<?php
if (!defined('WP_UNINSTALL_PLUGIN')) { exit; }
delete_option('heyhi_connector_settings');
// (Optional) keep logs for audit
