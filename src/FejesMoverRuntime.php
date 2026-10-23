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
    $theme = <<<'HTML'
<style id="fejes-theme-style">
.fmc-theme{float:right;display:inline-flex;gap:8px;align-items:center;margin:0 0 8px 16px}.fmc-theme select{width:auto!important;padding:5px 8px!important;border:1px solid #8888!important;border-radius:5px!important}
html[data-fejes-theme="light"]{--fejes-bg:#f5f6f8;--fejes-panel:#fff;--fejes-fg:#202632;--fejes-line:#c7cdd5;--fejes-link:#985000;--fejes-scheme:light}
html[data-fejes-theme="dark"]{--fejes-bg:#171b22;--fejes-panel:#222833;--fejes-fg:#edf0f5;--fejes-line:#4a5362;--fejes-link:#ffb567;--fejes-scheme:dark}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard,.fmc-mode){background:var(--fejes-bg)!important;color:var(--fejes-fg)!important;color-scheme:var(--fejes-scheme);border-radius:8px}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard){padding:18px!important}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard,.fmc-mode) :is(h1,h2,h3,p,span,strong,small,label,legend,summary,td,th,pre){color:var(--fejes-fg)!important}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard) :is(section,fieldset,.fm-card,.ms-card,.fms-panel,.fms-cards>div){background:var(--fejes-panel)!important;border-color:var(--fejes-line)!important}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard,.fmc-mode) :is(input,select,button,thead th,tbody td){background:var(--fejes-panel)!important;color:var(--fejes-fg)!important;border-color:var(--fejes-line)!important}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard,.fmc-mode) a{color:var(--fejes-link)!important}
html[data-fejes-theme] #fms .fms-primary{background:#a95206!important;color:#fff!important;border-color:#a95206!important}
html[data-fejes-theme] #fms .fms-danger{border-color:#d65b51!important}
html[data-fejes-theme] #fm-monitor .fm-donut span{background:var(--fejes-panel)!important}
@media(max-width:600px){.fmc-theme{float:none;display:flex;margin:0 0 10px}}
</style>
<label class="fmc-theme">THEME_LABEL <select data-fejes-theme-select aria-label="THEME_LABEL"><option value="auto">AUTO_LABEL</option><option value="light">LIGHT_LABEL</option><option value="dark">DARK_LABEL</option></select></label>
<script>(()=>{
if(window.fejesMoverTheme)return;window.fejesMoverTheme=true;
const key='fejesMoverTheme',valid=v=>['auto','light','dark'].includes(v)?v:'auto';
function apply(value){value=valid(value);if(value==='auto')document.documentElement.removeAttribute('data-fejes-theme');else document.documentElement.setAttribute('data-fejes-theme',value);document.querySelectorAll('[data-fejes-theme-select]').forEach(el=>el.value=value);}
function saved(){try{return valid(localStorage.getItem(key));}catch{return 'auto';}}
let choice=saved();apply(choice);document.addEventListener('change',event=>{if(!event.target.matches('[data-fejes-theme-select]'))return;const value=valid(event.target.value);try{localStorage.setItem(key,value);}catch{}choice=value;apply(choice);});
window.addEventListener('storage',event=>{if(event.key===key){choice=saved();apply(choice);}});
// Polling can replace the banner without executing scripts in the response.
new MutationObserver(()=>{const value=choice;document.querySelectorAll('[data-fejes-theme-select]').forEach(el=>{if(el.value!==value)el.value=value;});}).observe(document.body,{childList:true,subtree:true});
})();</script>
HTML;
    $theme=str_replace(['THEME_LABEL','AUTO_LABEL','LIGHT_LABEL','DARK_LABEL'],array_map($esc,[
        $t('Megjelenés','Appearance','Darstellung'),$t('Rendszerkövető','Follow Unraid','Unraid folgen'),
        $t('Világos','Light','Hell'),$t('Sötét','Dark','Dunkel')]),$theme);
    $banner=str_replace('<strong>', $theme.'<strong>',$banner);
    $token = @parse_ini_file('/var/local/emhttp/var.ini');
    return ['mode'=>$mode,'pool'=>$pool,'path'=>'/mnt/'.$pool,'mounted'=>$mounted,'pools'=>$pools,
        'error'=>$error,'lockError'=>$lockError,'readError'=>$readError,'configInvalid'=>!$valid,
        'pathConfig'=>$configPath,'raw'=>$raw === false ? '' : $raw,
        'hash'=>hash('sha256',$raw === false ? '' : $raw),'lock'=>$lock,
        'token'=>is_array($token) ? ($token['csrf_token'] ?? '') : '',
        't'=>$t,'esc'=>$esc,'banner'=>$banner];
})(!empty($fmcConfigWrite));
