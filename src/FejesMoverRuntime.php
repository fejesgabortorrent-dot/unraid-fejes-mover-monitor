<?php
// Shared, fail-closed runtime configuration. No settings or automation writes here.
return (static function ($configWrite) {
    $language = $_COOKIE['fejes_mover_lang'] ?? 'hu';
    if (!is_string($language) || !in_array($language, ['hu','en','de'], true)) $language = 'hu';
    $t = static fn($hu,$en,$de) => ['hu'=>$hu,'en'=>$en,'de'=>$de][$language];
    $esc = static fn($v) => htmlspecialchars((string)$v, ENT_QUOTES|ENT_SUBSTITUTE, 'UTF-8');
    $configPath = '/boot/config/plugins/fejes.mover.monitor/settings.json';
    $error = false;
    $lock = null;
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
        $lock = @fopen('/var/run/fejes-mover-config.lock', 'c');
        if (!$lock || !flock($lock, ($configWrite ? LOCK_EX : LOCK_SH)|LOCK_NB)) $error = true;
    }
    $lockError = $error;
    $raw = @file_get_contents($configPath);
    $readError = $raw === false && file_exists($configPath);
    if ($readError) $error = true;
    $config = $raw === false ? [] : json_decode($raw, true);
    $validName = static fn($name) => is_string($name) && preg_match('/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/D', $name);
    $valid = is_array($config) && ($raw === false || (
        ($config['version'] ?? null) === 1 &&
        in_array($config['mode'] ?? null, ['demo','observer','advanced'], true) &&
        $validName($config['pool'] ?? null)
    ));
    if (!$valid) $error = true;
    $mode = !$error && isset($config['mode']) ? $config['mode'] : 'observer';
    $pool = !$error && isset($config['pool']) ? $config['pool'] : 'cache';
    $mounts = [];
    foreach (explode("\n", @file_get_contents('/proc/self/mountinfo') ?: '') as $line) {
        $fields = explode(' ', $line);
        $mount = $fields[4] ?? '';
        if ($mount !== '') $mounts[$mount] = true;
    }
    $pools = [];
    // Use Unraid pool definitions; never accept a path supplied by the browser.
    foreach (glob('/boot/config/pools/*.cfg') ?: [] as $file) {
        $name = basename($file, '.cfg');
        if ($validName($name)) $pools[$name] = isset($mounts['/mnt/'.$name]);
    }
    if (!$pools && isset($mounts['/mnt/cache'])) $pools['cache'] = true;
    ksort($pools);
    $mounted = isset($pools[$pool]) && $pools[$pool];
    $modeText = [
        'demo'=>$t('Demó','Demo','Demo'),
        'observer'=>$t('Megfigyelő','Observer','Beobachter'),
        'advanced'=>$t('Haladó','Advanced','Erweitert'),
    ][$mode];
    $banner = '<div class="fmc-mode" style="margin:12px 16px;padding:12px;border:1px solid #8885;border-left:3px solid #ef7d00;border-radius:3px">';
    $banner .= '<strong>'.$esc($t('Mód: ','Mode: ','Modus: ').$modeText).'</strong> · ';
    $banner .= $mode === 'demo'
        ? $esc($t('Szimulált adatok. Nincs élő megfigyelés vagy scriptmentés.','Simulated data. No live monitoring or script saves.','Simulierte Daten. Keine Live-Überwachung oder Skriptspeicherung.'))
        : $esc($t('Figyelt pool: ','Monitored pool: ','Überwachter Pool: ').$pool);
    if ($error) $banner .= '<p role="alert">'.$esc($t('A konfiguráció nem olvasható biztonságosan. A szerkesztés tiltva.','Configuration cannot be safely read. Editing is disabled.','Konfiguration kann nicht sicher gelesen werden. Bearbeitung gesperrt.')).'</p>';
    $banner .= ' · <a href="/Tools/FejesMoverSetup">'.$esc($t('Mód és pool beállítása','Configure mode and pool','Modus und Pool einstellen')).'</a></div>';
    $token = @parse_ini_file('/var/local/emhttp/var.ini');
    return ['mode'=>$mode,'pool'=>$pool,'path'=>'/mnt/'.$pool,'mounted'=>$mounted,'pools'=>$pools,
        'error'=>$error,'lockError'=>$lockError,'readError'=>$readError,'configInvalid'=>!$valid,
        'pathConfig'=>$configPath,'raw'=>$raw === false ? '' : $raw,
        'hash'=>hash('sha256',$raw === false ? '' : $raw),'lock'=>$lock,
        'token'=>is_array($token) ? ($token['csrf_token'] ?? '') : '',
        't'=>$t,'esc'=>$esc,'banner'=>$banner];
})(!empty($fmcConfigWrite));
