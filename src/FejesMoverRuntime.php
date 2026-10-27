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
.fm-lang-control,.fm-icon-control{display:inline-flex!important;align-items:center!important;justify-content:center!important;width:44px!important;height:44px!important;min-width:44px;box-sizing:border-box;position:relative;margin:0!important;padding:0!important;border:1px solid #8792a066!important;border-radius:11px!important;background:var(--fejes-panel,#303641)!important;color:var(--fejes-fg,#edf0f5)!important;text-decoration:none!important;vertical-align:middle;cursor:pointer;box-shadow:inset 0 1px 0 #ffffff0a}
.fm-lang-control>span{display:flex!important;align-items:center;justify-content:center;width:26px!important;margin:0!important;pointer-events:none}.fm-lang-control>select{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;margin:0!important;padding:0!important;opacity:0!important;cursor:pointer}.fm-icon-control svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}.fm-lang-control:focus-within,.fm-icon-control:focus-visible{outline:2px solid #ed8b25;outline-offset:3px}@media(hover:hover){.fm-lang-control:hover,.fm-icon-control:hover{border-color:#ed8b25!important;background:#ed8b2520!important}}
@property --fm-orbit-angle{syntax:"<angle>";initial-value:0deg;inherits:false}
@keyframes fm-control-orbit{to{--fm-orbit-angle:360deg}}
:is(.fm-lang-control,.fm-icon-control)::before{content:"";position:absolute;inset:-1px;border-radius:inherit;padding:2px;background:conic-gradient(from var(--fm-orbit-angle),transparent 0deg,transparent 210deg,#ed8b25 280deg,#ffe2b0 310deg,transparent 360deg);-webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);-webkit-mask-composite:xor;mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);mask-composite:exclude;pointer-events:none;opacity:0;transition:opacity .15s}
@media(hover:hover){:is(.fm-lang-control,.fm-icon-control):hover::before{opacity:1;animation:fm-control-orbit 1.8s linear infinite}}
:is(.fm-lang-control,.fm-icon-control):focus-within::before{opacity:1;animation:fm-control-orbit 1.8s linear infinite}
@media(prefers-reduced-motion:reduce){:is(.fm-lang-control,.fm-icon-control)::before{animation:none!important;transition:none!important}}
#fejes-mover-dashboard .tile-header{display:flex!important;align-items:center!important;justify-content:space-between;gap:12px;flex-wrap:wrap}#fejes-mover-dashboard .tile-header-left{display:flex;align-items:center;min-width:0}#fejes-mover-dashboard .tile-header-right{display:inline-flex!important;align-items:center!important;gap:8px!important;margin-left:auto;float:none!important;white-space:nowrap}#fejes-mover-dashboard .tile-header-main{margin:0!important}html[data-fejes-theme] #fejes-mover-dashboard .tile-header-right a.fm-icon-control{color:var(--fejes-fg,#edf0f5)!important}
.fmc-theme{float:right;display:inline-flex;gap:8px;align-items:center;margin:0 0 8px 16px}.fmc-theme select{width:auto!important;padding:5px 8px!important;border:1px solid #8888!important;border-radius:5px!important}
html[data-fejes-theme="auto"]{--fejes-bg:var(--background-color,#1d1b1b);--fejes-panel:var(--mild-background-color,#262626);--fejes-fg:var(--text-color,#f2f2f2);--fejes-line:var(--border-color,#404040);--fejes-link:var(--link-text-color,#486dba);--fejes-scheme:inherit}
html[data-fejes-theme="white"]{--fejes-bg:#f2f2f2;--fejes-panel:#f7f9f9;--fejes-fg:#1d1b1b;--fejes-line:#d3d3d3;--fejes-link:#486dba;--fejes-scheme:light}
html[data-fejes-theme="black"]{--fejes-bg:#1d1b1b;--fejes-panel:#262626;--fejes-fg:#f2f2f2;--fejes-line:#404040;--fejes-link:#486dba;--fejes-scheme:dark}
html[data-fejes-theme="gray"]{--fejes-bg:#1d1b1b;--fejes-panel:#121510;--fejes-fg:#606e7f;--fejes-line:#606e7f;--fejes-link:#486dba;--fejes-scheme:dark}
html[data-fejes-theme="azure"]{--fejes-bg:#e8e8e8;--fejes-panel:#edeaef;--fejes-fg:#606e7f;--fejes-line:#606e7f;--fejes-link:#486dba;--fejes-scheme:light}
html[data-fejes-theme="light"]{--fejes-bg:#f5f6f8;--fejes-panel:#fff;--fejes-fg:#202632;--fejes-line:#c7cdd5;--fejes-link:#985000;--fejes-scheme:light}
html[data-fejes-theme="dark"]{--fejes-bg:#171b22;--fejes-panel:#222833;--fejes-fg:#edf0f5;--fejes-line:#4a5362;--fejes-link:#ffb567;--fejes-scheme:dark}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard,.fmc-mode){background:var(--fejes-bg)!important;color:var(--fejes-fg)!important;color-scheme:var(--fejes-scheme);border-radius:8px}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard){padding:18px!important}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard,.fmc-mode) :is(h1,h2,h3,p,span,strong,small,label,legend,summary,td,th,pre):not(#fmd-status){color:var(--fejes-fg)!important}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard) :is(section,fieldset,.fm-card,.ms-card,.fms-panel,.fms-cards>div){background:var(--fejes-panel)!important;border-color:var(--fejes-line)!important}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard,.fmc-mode) :is(input,select,button,thead th,tbody td){background:var(--fejes-panel)!important;color:var(--fejes-fg)!important;border-color:var(--fejes-line)!important}
html[data-fejes-theme] :is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard,.fmc-mode) a{color:var(--fejes-link)!important}
html[data-fejes-theme] #fms .fms-primary{background:#a95206!important;color:#fff!important;border-color:#a95206!important}
html[data-fejes-theme] #fms .fms-danger{border-color:#d65b51!important}
html[data-fejes-theme] #fmd-percent{background:var(--fejes-panel)!important;color:var(--fejes-fg)!important}
html[data-fejes-theme] #fm-monitor .fm-donut span{background:var(--fejes-panel)!important}
@media(max-width:600px){.fmc-theme{float:none;display:flex;margin:0 0 10px}}
</style>
<label class="fmc-theme">THEME_LABEL <select data-fejes-theme-select aria-label="THEME_LABEL"><option value="auto">AUTO_LABEL</option><option value="white">WHITE_PALETTE_LABEL</option><option value="black">BLACK_PALETTE_LABEL</option><option value="gray">GRAY_PALETTE_LABEL</option><option value="azure">AZURE_PALETTE_LABEL</option></select></label>
<script>(()=>{
if(window.fejesMoverTheme)return;window.fejesMoverTheme=true;
const key='fejesMoverTheme',valid=v=>{v=({light:'white',dark:'black'})[v]||v;return ['auto','white','black','gray','azure'].includes(v)?v:'auto';};
function apply(value){value=valid(value);document.documentElement.setAttribute('data-fejes-theme',value);document.querySelectorAll('[data-fejes-theme-select]').forEach(el=>el.value=value);}
function saved(){try{return valid(localStorage.getItem(key));}catch{return 'auto';}}
let choice=saved();apply(choice);document.addEventListener('change',event=>{if(!event.target.matches('[data-fejes-theme-select]'))return;const value=valid(event.target.value);try{localStorage.setItem(key,value);}catch{}choice=value;apply(choice);});
window.addEventListener('storage',event=>{if(event.key===key){choice=saved();apply(choice);}});
// Polling can replace the banner without executing scripts in the response.
new MutationObserver(()=>{const value=choice;document.querySelectorAll('[data-fejes-theme-select]').forEach(el=>{if(el.value!==value)el.value=value;});}).observe(document.body,{childList:true,subtree:true});
})();</script>
HTML;
    $theme=str_replace(['THEME_LABEL','AUTO_LABEL','LIGHT_LABEL','DARK_LABEL','WHITE_PALETTE_LABEL','BLACK_PALETTE_LABEL','GRAY_PALETTE_LABEL','AZURE_PALETTE_LABEL'],array_map($esc,[
        $t('Megjelenés','Appearance','Darstellung'),$t('Rendszerkövető','Follow Unraid','Unraid folgen'),
        $t('Világos','Light','Hell'),$t('Sötét','Dark','Dunkel'),$t('Unraid · Fehér','Unraid · White','Unraid · Weiß'),$t('Unraid · Fekete','Unraid · Black','Unraid · Schwarz'),$t('Unraid · Szürke','Unraid · Gray','Unraid · Grau'),$t('Unraid · Azúr','Unraid · Azure','Unraid · Azur')]),$theme);
    $design = <<<'HTML'
<style id="fejes-depth-style">
#fms button.fms-sort-heading{background:transparent!important;color:inherit!important;border:0!important;padding:0!important;margin:0!important;box-shadow:none!important;transform:none!important;text-align:left;font:inherit;font-weight:600;display:flex;align-items:center;gap:6px;width:100%;min-height:44px}#fms .fms-sort-controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 18px}#fms .fms-sort-controls small{opacity:.7;font-size:12px}#fms .fms-sort-controls select{max-width:100%}#fms .fms-sort-controls button{min-width:130px}
#fejes-mover-dashboard .fmc-nav,#fejes-mover-dashboard .fmc-depth{display:none}#fejes-mover-dashboard .fmc-mode{margin:8px!important;font-size:12px}#fejes-mover-dashboard .fmc-theme{float:none;display:flex;margin:0 0 8px}
/* Comfortable flat controls, including the compact dashboard appearance picker. */
.fmc-theme{flex-wrap:wrap;row-gap:6px}.fmc-theme select{min-width:155px!important;max-width:100%;min-height:44px;padding:8px 30px 8px 12px!important;border-radius:10px!important;font:inherit;font-weight:600;box-sizing:border-box;cursor:pointer}
:is(.fmc-theme,.fmc-depth) select{border:1px solid #8888!important;transition:border-color .15s ease,background-color .15s ease}
@media(hover:hover){:is(.fmc-theme,.fmc-depth) select:hover{border-color:#ed8b25!important}.fmc-nav :is(a,button:enabled):hover{border-color:#ed8b25!important;background-color:#ed8b2514!important}}
html[data-fejes-depth="flat"] :is(.fmc-nav a,.fmc-nav button,#fms button:not(.fms-sort-heading),#ms button,#fp button,#fm-monitor button,#fmc-setup button,#fejes-mover-dashboard button){border-radius:10px!important;box-shadow:none;transition:border-color .15s ease,background-color .15s ease}
html[data-fejes-depth="flat"] .fmc-nav a[aria-current="page"]{box-shadow:inset 0 -2px #ed8b25}
@media(prefers-reduced-motion:reduce){:is(.fmc-theme,.fmc-depth) select,html[data-fejes-depth="flat"] :is(.fmc-nav a,.fmc-nav button,#fms button,#ms button,#fmc-setup button){transition:none}}
/* Scoped to Fejes Mover; host navigation and system preferences stay independent. */
.fmc-nav{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:16px;padding:12px;border:1px solid #8885;border-radius:14px;background:#8881}
.fmc-nav a,.fmc-nav button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 14px;border:1px solid #8886;border-radius:9px;color:inherit!important;background:transparent;text-decoration:none!important;font:inherit;font-weight:600;box-sizing:border-box;cursor:pointer}
.fmc-nav a[aria-current="page"]{border-color:#dd8126;background:#ed8b2520;box-shadow:inset 0 -3px #ed8b25}
.fmc-nav button:disabled{opacity:.4;cursor:default}.fmc-nav .fmc-nav-pages{display:flex;flex-wrap:wrap;gap:8px;margin-left:auto}
html[data-fejes-theme] :is(.fmc-nav,.fmc-depth){background:var(--fejes-panel)!important;color:var(--fejes-fg)!important;border-color:var(--fejes-line)!important}html[data-fejes-theme] :is(.fmc-nav,.fmc-depth) :is(a,button,select){color:var(--fejes-fg)!important;background:var(--fejes-panel)!important;border-color:var(--fejes-line)!important}html[data-fejes-theme] .fmc-nav a[aria-current="page"]{border-color:#dd8126!important;background:#ed8b2520!important}html[data-fejes-theme] #fms .fms-cards>div{border-top-color:#ed8b25!important}
.fmc-depth{display:inline-flex;gap:8px;align-items:center;margin:8px 16px;padding:8px 12px;border:1px solid #8885;border-radius:12px}.fmc-depth select{width:auto!important;min-height:44px;padding:7px 10px!important;border-radius:8px!important}
:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard){line-height:1.55}
:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,#fejes-mover-dashboard) :is(button,select,input[type="search"],input[type="number"]){min-height:44px;box-sizing:border-box;border-radius:8px!important}
:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup,.fmc-mode,.fmc-nav,.fmc-depth) :is(a,button,input,select,summary):focus-visible{outline:3px solid #ed8b25!important;outline-offset:3px}
#fms{max-width:1280px!important;box-sizing:border-box}#fms .fms-toolbar{margin:12px 0 24px}#fms .fms-toolbar h2{font-size:24px;letter-spacing:-.45px}#fms .fms-toolbar>div>span{opacity:.75}
#fms .fms-cards{gap:16px;margin:24px 0}#fms .fms-cards>div{padding:20px!important;border-top:3px solid #ed8b25!important;min-width:0;box-sizing:border-box}#fms .fms-cards strong{font-size:21px;letter-spacing:-.4px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}#fms .fms-cards span{font-size:13px;font-weight:600}
#fms .fms-panel,#fms #fms-waiting{border-radius:12px!important;padding:20px!important}#fms details.fms-panel>summary{min-height:30px;padding:4px 0;cursor:pointer}#fms details.fms-panel[open]>summary{margin-bottom:18px;border-bottom:1px solid #8884;padding-bottom:16px}
#fms .fms-filters{padding:12px 0;gap:12px}#fms .fms-filters input[type="search"]{flex:1 1 260px;min-width:0!important;border:1px solid #8887;padding:10px 14px!important}#fms .fms-filters label{display:flex;align-items:center;gap:8px;min-height:44px}#fms .fms-count{font-size:13px;opacity:.75;white-space:nowrap}
#fms table.fms-queue th{font-size:12px;letter-spacing:.2px;line-height:1.5;padding:14px 12px!important}#fms table.fms-queue td{padding:18px 12px!important;border-bottom:1px solid #8883;line-height:1.6}#fms table.fms-queue tbody tr:last-child td{border-bottom:0}#fms table.fms-queue td:nth-child(2),#fms table.fms-queue td:nth-child(3){font-variant-numeric:tabular-nums}#fms .fms-file summary{font-weight:600}#fms .fms-file small{font-size:12px}#fms table.fms-queue td:last-child{font-size:13px;font-weight:600}
#fms fieldset{border:1px solid #8884;border-radius:10px;margin:16px 0;padding:18px;min-width:0}#fms legend{padding:0 8px;font-weight:600}#fms fieldset p{font-size:13px;opacity:.85;margin-bottom:0}#fms .fms-ratio-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:10px}#fms .fms-ratio-controls input[type="range"]{flex:1 1 180px;min-width:0}#fms input[type="number"]{max-width:140px;padding:8px 12px;border:1px solid #8887}
html[data-fejes-depth="raised"] :is(#fm-monitor .fm-card,#fms .fms-cards>div,#fms .fms-panel,#fms #fms-waiting,#ms .box,#ms .hero,#fejes-mover-dashboard,#fmc-setup fieldset){border-radius:14px!important;box-shadow:0 14px 28px -20px #000a,0 4px 8px -6px #0007,inset 0 1px 0 #ffffff28!important;position:relative}
html[data-fejes-depth="raised"] #fms .fms-cards>div{background-image:linear-gradient(145deg,#ffffff09,transparent 65%)!important}
html[data-fejes-depth="raised"] #fm-monitor .fm-flow span{border:1px solid #8886;border-bottom:4px solid #8888;border-radius:10px;padding:12px 16px;box-shadow:0 8px 16px -10px #0009;display:inline-block}
html[data-fejes-depth="raised"] :is(.fmc-nav a,.fmc-nav button:enabled,#fms button:enabled,#ms button:enabled,#fmc-setup button:enabled){box-shadow:0 3px 0 -1px #0005,inset 0 1px 0 #ffffff25;transition:transform .15s ease,box-shadow .15s ease}
@media(hover:hover){html[data-fejes-depth="raised"] :is(.fmc-nav a,.fmc-nav button:enabled,#fms button:enabled,#ms button:enabled,#fmc-setup button:enabled):hover{transform:translateY(-1px);box-shadow:0 5px 0 -2px #0005,inset 0 1px 0 #ffffff35}}
html[data-fejes-depth="raised"] :is(.fmc-nav a,.fmc-nav button:enabled,#fms button:enabled,#ms button:enabled,#fmc-setup button:enabled):active{transform:translateY(1px);box-shadow:inset 0 2px 4px #0003}
html[data-fejes-theme="light"][data-fejes-depth="raised"] :is(#fms .fms-cards>div,#fms .fms-panel,#fms #fms-waiting){box-shadow:0 14px 26px -20px #26354b60,0 3px 6px -4px #26354b30,inset 0 1px 0 #fff!important}
html[data-fejes-theme="dark"] #fms table.fms-queue th{background:#283140!important}
@media(max-width:700px){#fms .fms-queue-scroll{max-height:none!important;overflow:visible!important}.fmc-nav .fmc-nav-pages{margin-left:0;flex:1 1 100%;display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.fmc-nav a,.fmc-nav button{padding:0 10px}.fmc-nav{margin:12px 8px}.fmc-depth{margin-left:12px}#fms{padding:12px!important;margin:12px auto!important}#fms .fms-cards{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:10px}#fms .fms-cards>div{padding:14px!important}#fms .fms-cards strong{font-size:18px}#fms .fms-panel,#fms #fms-waiting{padding:14px!important}#fms .fms-toolbar{align-items:stretch}#fms .fms-toolbar>button{width:100%;margin:0!important}#fms .fms-filters{align-items:stretch}#fms .fms-filters select{max-width:100%;flex:1 1 180px}#fms table.fms-queue{min-width:0!important}#fms table.fms-queue thead{display:none}#fms table.fms-queue tbody,#fms table.fms-queue tr,#fms table.fms-queue td{display:block;width:auto!important}#fms table.fms-queue tr{margin:10px 0 16px;border:1px solid #8885;border-radius:10px;overflow:hidden}#fms table.fms-queue td{padding:8px 12px!important;border:0}#fms table.fms-queue td:first-child{padding-top:14px!important}#fms table.fms-queue td:last-child{padding-bottom:14px!important}#fms table.fms-queue td::before{content:attr(data-fejes-label);display:block;font-size:11px;opacity:.7;font-weight:400}#fms table.fms-queue tr[hidden]{display:none!important}#fms fieldset>label{display:inline-flex;align-items:center;min-height:44px;margin-right:14px!important}#fm-monitor .fm-flow{flex-wrap:wrap!important}}
@media(max-width:380px){#fms .fms-cards{grid-template-columns:1fr!important}}
@media(prefers-reduced-motion:reduce){:is(#fm-monitor,#fms,#ms,#fmc-setup,#fejes-mover-dashboard,.fmc-nav) *{animation:none!important;transition:none!important;transform:none!important}}

.fm-summary{position:relative;border:1px solid #8885;border-left:3px solid #ef8b24;border-radius:10px;padding:12px;margin:14px 0;line-height:1.5;overflow-wrap:anywhere}.fm-summary p{white-space:normal!important;margin:5px 0;font-size:12px}.fm-hover-help{display:inline-block;position:relative;margin-right:8px}.fm-hover-help summary{cursor:help;list-style:none;padding:3px 8px;border:1px solid #8886;border-radius:50%}.fm-hover-help>div{white-space:normal!important;overflow-wrap:anywhere;display:none;position:absolute;bottom:100%;left:0;width:min(270px,70vw);box-sizing:border-box;padding:12px;border:1px solid #888;border-radius:10px;background:var(--fejes-panel,#242a34);color:var(--fejes-fg,#eef1f6);box-shadow:0 8px 24px #0006;z-index:20;font-size:13px}.fm-hover-help[open]>div,.fm-hover-help:hover>div,.fm-hover-help:focus-within>div{display:block}

/* Consistent layout and stable control positions on every full plugin page. */
:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup){box-sizing:border-box!important;max-width:1280px!important;margin:24px auto!important;padding-left:20px!important;padding-right:20px!important}
.fmc-nav{position:sticky;top:44px;z-index:8;flex-wrap:nowrap;background:var(--fejes-panel,#242a34);color:var(--fejes-fg,#eef1f6);box-shadow:0 5px 16px #0003;overflow-x:auto;scrollbar-width:thin;isolation:isolate}
.fmc-nav .fmc-nav-pages{flex-wrap:nowrap}.fmc-nav :is(a,button){flex-shrink:0;white-space:nowrap;min-width:104px}
:is(.fmc-nav,#fms,#fm-monitor,#ms,#fp,#fmc-setup) button:not(.fms-sort-heading),.fmc-nav a{min-height:44px!important;box-sizing:border-box!important;border-radius:10px!important;font-size:14px!important;font-weight:600!important;line-height:1.35!important;letter-spacing:normal!important;text-transform:none!important;transform:none!important;vertical-align:middle}
:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup) button:not(.fms-sort-heading):not(.fms-help){min-width:120px;padding:10px 16px!important;margin:4px!important}
:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup) button:disabled{cursor:not-allowed;opacity:.5}
:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup) :is(input,select){font-size:14px!important;line-height:1.4!important}
:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup) :is(h1,h2,h3){line-height:1.35;overflow-wrap:anywhere}
@media(max-width:700px){.fmc-nav{top:40px;margin:10px 6px;padding:8px;gap:6px}.fmc-nav :is(a,button){min-width:92px;padding:0 10px}.fmc-nav .fmc-nav-pages{gap:6px;margin-left:0}:is(#fms,#fm-monitor,#ms,#fp,#fmc-setup){padding-left:10px!important;padding-right:10px!important}}

.content:has(> .fmc-nav){overflow:visible!important}
.fmc-page-tail{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end;margin:24px 0;padding:12px 0;border-top:1px solid #8884}.fmc-support-strip{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;width:100%;padding:16px;box-sizing:border-box;background:#42464b;color:#fff;border:1px solid #fff;border-radius:10px}.fmc-support-strip small{flex-basis:100%;text-align:center}.fmc-support-strip strong{font-size:18px}.fmc-support-strip a{background:#555b62!important;color:#fff!important;border-color:#fff!important}.fmc-page-tail :is(a,button){display:inline-flex;align-items:center;justify-content:center;min-height:44px;min-width:140px;padding:0 16px;border:1px solid #8886;border-radius:10px;text-decoration:none;color:inherit;font-weight:600;background:#8881;box-sizing:border-box}

.fmc-mode{display:flow-root!important;box-sizing:border-box}.fmc-mode .fmc-theme{float:none!important;display:flex!important;justify-content:flex-end;align-items:center;flex-wrap:wrap;gap:8px;margin:0 0 10px!important}.fmc-mode .fmc-theme select{margin:0!important;min-height:44px;max-width:100%;box-sizing:border-box}.fmc-mode .fmc-theme label{margin:0!important}
</style>
<label class="fmc-depth">DEPTH_LABEL <select data-fejes-depth-select aria-label="DEPTH_LABEL"><option value="raised">RAISED_LABEL</option><option value="flat">FLAT_LABEL</option></select></label>
<span id="fejes-mover-top"></span><nav class="fmc-nav" aria-label="NAV_LABEL"><button type="button" data-fejes-back disabled>← BACK_LABEL</button><button type="button" data-fejes-forward disabled>FORWARD_LABEL →</button><a href="/Dashboard">⌂ HOME_LABEL</a><span class="fmc-nav-pages"><a href="/Tools/FejesMover">MONITOR_LABEL</a><a href="/Tools/FejesMoverSelective">MOVE_LABEL</a><a href="/Tools/FejesMoverSettings">SETTINGS_LABEL</a><a href="/Tools/FejesMoverSetup">SETUP_LABEL</a></span></nav>
<script>(()=>{
if(window.fejesMoverDepth)return;window.fejesMoverDepth=true;
const key='fejesMoverDepth',valid=v=>v==='flat'?'flat':'raised';let choice='raised';
try{choice=valid(localStorage.getItem(key));}catch{}
function apply(){document.documentElement.setAttribute('data-fejes-depth',choice);document.querySelectorAll('[data-fejes-depth-select]').forEach(el=>{el.value=choice;});}apply();
document.addEventListener('change',event=>{if(!event.target.matches('[data-fejes-depth-select]'))return;choice=valid(event.target.value);try{localStorage.setItem(key,choice);}catch{}apply();});
window.addEventListener('storage',event=>{if(event.key!==key)return;try{choice=valid(localStorage.getItem(key));}catch{choice='raised';}apply();});
new MutationObserver(()=>{document.querySelectorAll('[data-fejes-depth-select]').forEach(el=>{if(el.value!==choice)el.value=choice;});}).observe(document.body,{childList:true,subtree:true});
})();</script>
<script>(()=>{
if(window.fejesMoverNavigation)return;window.fejesMoverNavigation=true;
const allowed=['/Dashboard','/Tools/FejesMover','/Tools/FejesMoverSelective','/Tools/FejesMoverSettings','/Tools/FejesMoverSetup'],key='fejesMoverNavigation';let state={items:[],index:-1};
function load(){try{const v=JSON.parse(sessionStorage.getItem(key));if(v&&Array.isArray(v.items)&&v.items.length<=50&&v.items.every(p=>allowed.includes(p))&&Number.isInteger(v.index)&&v.index>=0&&v.index<v.items.length)state=v;}catch{}}
function save(){try{sessionStorage.setItem(key,JSON.stringify(state));}catch{}}
const path=location.pathname;load();
if(allowed.includes(path)&&state.items[state.index]!==path){state.items=state.items.slice(0,state.index+1);state.items.push(path);if(state.items.length>50)state.items.shift();state.index=state.items.length-1;save();}
function sync(){const main=document.querySelector('#fms,#fm-monitor,#ms,#fp,#fmc-setup');if(main&&!main.querySelector('.fmc-page-tail')){const tail=document.createElement('div');tail.className='fmc-page-tail';const top=document.createElement('button');top.type='button';top.addEventListener('click',event=>{event.preventDefault();window.scrollTo({top:0,left:0,behavior:'auto'});});top.textContent='↑ TOP_LABEL';const strip=document.createElement('div');strip.className='fmc-support-strip';const brand=document.createElement('strong');brand.textContent='PayPal';strip.append(brand);[['☕ COFFEE_LABEL · 2 €','/2EUR'],['🍺 BEER_LABEL · 5 €','/5EUR'],['🍕 Pizza · 10 €','/10EUR'],['💛 CUSTOM_LABEL','']].forEach(([label,amount])=>{const support=document.createElement('a');support.href='https://paypal.me/FejesG'+amount;support.target='_blank';support.rel='noopener noreferrer';support.textContent=label;strip.append(support);});const note=document.createElement('small');note.textContent='OPTIONAL_LABEL';strip.append(note);tail.append(strip,top);main.append(tail);}document.querySelectorAll('[data-fejes-back]').forEach(b=>{b.disabled=state.index<=0;});document.querySelectorAll('[data-fejes-forward]').forEach(b=>{b.disabled=state.index>=state.items.length-1;});document.querySelectorAll('.fmc-nav a').forEach(a=>{if(a.getAttribute('href')===path)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});const heads=Array.from(document.querySelectorAll('#fms table.fms-queue thead th'));document.querySelectorAll('#fms table.fms-queue tbody tr').forEach(row=>Array.from(row.children).forEach((cell,i)=>{const label=heads[i]?.textContent.replace(/[↑↓↕]/g,'').trim();if(label&&cell.getAttribute('data-fejes-label')!==label)cell.setAttribute('data-fejes-label',label);}));}
document.addEventListener('click',event=>{let step=event.target.closest('[data-fejes-back]')?-1:event.target.closest('[data-fejes-forward]')?1:0;if(!step)return;load();const i=state.index+step;if(i<0||i>=state.items.length)return;state.index=i;save();location.assign(state.items[i]);});
sync();new MutationObserver(sync).observe(document.body,{childList:true,subtree:true});
})();</script>
HTML;
    $design=str_replace(['COFFEE_LABEL','BEER_LABEL','CUSTOM_LABEL','SUPPORT_LABEL','OPTIONAL_LABEL','TOP_LABEL','DEPTH_LABEL','RAISED_LABEL','FLAT_LABEL','NAV_LABEL','BACK_LABEL','FORWARD_LABEL','HOME_LABEL','MONITOR_LABEL','MOVE_LABEL','SETTINGS_LABEL','SETUP_LABEL'],array_map($esc,[
        $t('Kávé','Coffee','Kaffee'),$t('Sör','Beer','Bier'),$t('Más összeg','Other amount','Anderer Betrag'),$t('Fejlesztés támogatása','Support development','Entwicklung unterstützen'),$t('Önkéntes · minden funkció ingyenes','Optional · all features are free','Freiwillig · alle Funktionen kostenlos'),$t('Lap tetejére','Back to top','Zum Seitenanfang'),$t('Térhatás','Depth','Tiefe'),$t('Térhatású kártyák','Raised cards','Erhabene Karten'),$t('Sík megjelenés','Flat appearance','Flache Darstellung'),
        $t('Mover navigáció','Mover navigation','Mover-Navigation'),$t('Vissza','Back','Zurück'),$t('Előre','Forward','Vorwärts'),$t('Főoldal','Home','Startseite'),
        $t('Mover figyelő','Monitor','Monitor'),$t('Mozgatás','Movement','Verschieben'),$t('Beállítások','Settings','Einstellungen'),$t('Mód és pool','Mode and pool','Modus und Pool')]),$design);
    $banner=str_replace('<strong>', $theme.'<strong>',$banner);
    // Dashboard polling keeps only .fmc-mode: carry the shared stylesheet with it.
    $designStyleEnd = strpos($design, '</style>') + strlen('</style>');
    $banner = substr_replace($banner, substr($design, 0, $designStyleEnd), strrpos($banner, '</div>'), 0);
    $banner .= substr($design, $designStyleEnd);
    // Aggregate report only. No scans, torrent queries or writes during UI refresh.
    $summary='';
    if($mode==='advanced'&&$pool==='cache'){
        $lastPath='/boot/config/plugins/fejes.mover.monitor/selective-last.json';
        $last=is_link($lastPath)?null:json_decode(@file_get_contents($lastPath)?:'null',true);
        $labels=['running'=>$t('Ellenőrzés vagy mozgatás folyamatban','Checks or movement in progress','Prüfung oder Verschieben läuft'),'completed'=>$t('Befejezve, fájlok ellenőrizve','Completed, files verified','Abgeschlossen, Dateien geprüft'),'deferred'=>$t('Védelmi feltétel miatt várakozik','Waiting for a safety condition','Wartet auf Schutzbedingung'),'error'=>$t('Hiba: részletek ellenőrzése szükséges','Error: review details','Fehler: Details prüfen'),'nothing_eligible'=>$t('Nincs alkalmas fájl','No eligible files','Keine geeigneten Dateien'),'no_files_moved'=>$t('Ellenőrzés kész, mozgatás nélkül','Checks finished, no files moved','Prüfung beendet, keine Dateien verschoben')];
        $reasons=['capacity'=>$t('Szabadhely-küszöb','Free-space threshold','Freiplatzgrenze'),'cooldown'=>$t('Két kör közötti várakozás','Batch cooldown','Wartezeit zwischen Läufen'),'integrity'=>$t('Integritásvédelem','Integrity protection','Integritätsschutz'),'backup'=>$t('Biztonsági mentés','Backup','Sicherung'),'parity'=>$t('Paritásellenőrzés','Parity check','Paritätsprüfung')];
        $status=$t('Nincs olvasható jelentés','No readable report','Kein lesbarer Bericht');$detail='';
        if(is_array($last)){
            $status=$labels[$last['state']??'']??$t('Nem ellenőrizhető állapot','Unverified state','Ungeprüfter Zustand');
            if(($last['requires_inspection']??false)===true)$status=$t('Beavatkozás szükséges · mozgatás tiltva','Inspection required · movement blocked','Prüfung erforderlich · Verschieben gesperrt');
            if(!empty($last['inspection_resolution'])&&($last['state']??'')==='error'&&empty($last['requires_inspection']))$status=$t('Helyreállítás ellenőrizve · új körre vár','Recovery inspected · awaiting a new run','Wiederherstellung geprüft · wartet auf neuen Lauf');
            if(is_numeric($last['started']??null))$detail=$t('Jelentés ideje: ','Report time: ','Berichtszeit: ').date('Y-m-d H:i',(int)$last['started']);
            if(($last['state']??'')==='completed'&&is_numeric($last['moved_files']??null)&&is_numeric($last['moved_bytes']??null))$detail.=' · '.$last['moved_files'].' '.$t('fájl','files','Dateien').' · '.number_format($last['moved_bytes']/1073741824,2).' GiB';
            if(($last['state']??'')==='error'&&($last['error_code']??'')==='torrent_snapshot_unavailable')$detail.=' · '.$t('A torrentállapot nem kérdezhető le; a biztonság nem igazolható.','Torrent state could not be queried; safety could not be verified.','Torrentstatus konnte nicht abgefragt werden; Sicherheit nicht verifiziert.');
            if(is_array($last['blockers']??null)&&$last['blockers'])$detail.=' · '.implode(', ',array_map(static fn($key)=>$reasons[$key]??$t('További védelmi feltétel','Additional guard','Weitere Schutzbedingung'),$last['blockers']));
        }
        $tip=$t('A legutóbbi jelentés pillanatkép. A futó háttérfolyamat önmagában nem bizonyít adatátvitelt. A Részletek oldalon látható a várólista és a védelmek.','The last report is a snapshot. A running worker alone does not prove data transfer. Open Details for the queue and guards.','Der letzte Bericht ist eine Momentaufnahme. Ein laufender Prozess allein beweist keinen Datentransfer. Details zeigen Warteliste und Schutzbedingungen.');
        $summary='<section class="fm-summary" aria-label="'.$esc($t('Mozgatási jelentés','Movement report','Verschiebebericht')).'"><strong>'.$esc($status).'</strong><p>'.$esc($detail).'</p><details class="fm-hover-help"><summary aria-label="'.$esc($t('Állapotsúgó','Status help','Statushilfe')).'">ⓘ</summary><div>'.$esc($tip).'</div></details> <a href="/Tools/FejesMoverSelective">'.$esc($t('Részletek és várólista →','Details and queue →','Details und Warteliste →')).'</a></section>';
    }

    $token = @parse_ini_file('/var/local/emhttp/var.ini');
    return ['mode'=>$mode,'pool'=>$pool,'path'=>'/mnt/'.$pool,'mounted'=>$mounted,'pools'=>$pools,
        'error'=>$error,'lockError'=>$lockError,'readError'=>$readError,'configInvalid'=>!$valid,
        'pathConfig'=>$configPath,'raw'=>$raw === false ? '' : $raw,
        'hash'=>hash('sha256',$raw === false ? '' : $raw),'lock'=>$lock,
        'token'=>is_array($token) ? ($token['csrf_token'] ?? '') : '',
        't'=>$t,'esc'=>$esc,'banner'=>$banner,'summary'=>$summary];
})(!empty($fmcConfigWrite));
