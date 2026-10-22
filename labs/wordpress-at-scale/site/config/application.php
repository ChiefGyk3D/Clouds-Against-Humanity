<?php
// SPDX-License-Identifier: Apache-2.0
// Site configuration as code. Every secret comes from the environment (put there by the
// secrets manager at deploy time); nothing sensitive is written in this file.

function env_required(string $name): string {
    $value = getenv($name);
    if ($value === false || $value === '') {
        throw new RuntimeException("missing environment variable: $name");
    }
    return $value;
}

define('DB_NAME', env_required('DB_NAME'));
define('DB_USER', env_required('DB_USER'));
define('DB_PASSWORD', env_required('DB_PASSWORD'));
define('DB_HOST', env_required('DB_HOST'));
define('AUTH_KEY', env_required('AUTH_KEY'));

// Nobody changes code from the admin screen of a running node: updates arrive as a new release.
define('DISALLOW_FILE_MODS', true);
define('DISALLOW_FILE_EDIT', true);

// Scheduled jobs run from a real scheduler (one place), not from every page load on every node.
define('DISABLE_WP_CRON', true);
