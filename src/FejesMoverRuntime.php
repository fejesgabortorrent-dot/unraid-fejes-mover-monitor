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
    $design = <<<'HTML'
<style id="fejes-depth-style">
#fms button.fms-sort-heading{background:transparent!important;color:inherit!important;border:0!important;padding:0!important;margin:0!important;box-shadow:none!important;transform:none!important;text-align:left;font:inherit;font-weight:600;display:flex;align-items:center;gap:6px;width:100%;min-height:44px}#fms .fms-sort-controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 18px}#fms .fms-sort-controls small{opacity:.7;font-size:12px}#fms .fms-sort-controls select{max-width:100%}#fms .fms-sort-controls button{min-width:130px}
#fejes-mover-dashboard .fmc-nav,#fejes-mover-dashboard .fmc-depth{display:none}#fejes-mover-dashboard .fmc-mode{margin:8px!important;font-size:12px}#fejes-mover-dashboard .fmc-theme{float:none;display:flex;margin:0 0 8px}
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
</style>
<label class="fmc-depth">DEPTH_LABEL <select data-fejes-depth-select aria-label="DEPTH_LABEL"><option value="raised">RAISED_LABEL</option><option value="flat">FLAT_LABEL</option></select></label>
<nav class="fmc-nav" aria-label="NAV_LABEL"><button type="button" data-fejes-back disabled>← BACK_LABEL</button><button type="button" data-fejes-forward disabled>FORWARD_LABEL →</button><a href="/Dashboard">⌂ HOME_LABEL</a><span class="fmc-nav-pages"><a href="/Tools/FejesMover">MONITOR_LABEL</a><a href="/Tools/FejesMoverSelective">MOVE_LABEL</a><a href="/Tools/FejesMoverSettings">SETTINGS_LABEL</a><a href="/Tools/FejesMoverSetup">SETUP_LABEL</a></span></nav>
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
function sync(){document.querySelectorAll('[data-fejes-back]').forEach(b=>{b.disabled=state.index<=0;});document.querySelectorAll('[data-fejes-forward]').forEach(b=>{b.disabled=state.index>=state.items.length-1;});document.querySelectorAll('.fmc-nav a').forEach(a=>{if(a.getAttribute('href')===path)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});const heads=Array.from(document.querySelectorAll('#fms table.fms-queue thead th'));document.querySelectorAll('#fms table.fms-queue tbody tr').forEach(row=>Array.from(row.children).forEach((cell,i)=>{const label=heads[i]?.textContent.replace(/[↑↓↕]/g,'').trim();if(label&&cell.getAttribute('data-fejes-label')!==label)cell.setAttribute('data-fejes-label',label);}));}
document.addEventListener('click',event=>{let step=event.target.closest('[data-fejes-back]')?-1:event.target.closest('[data-fejes-forward]')?1:0;if(!step)return;load();const i=state.index+step;if(i<0||i>=state.items.length)return;state.index=i;save();location.assign(state.items[i]);});
sync();new MutationObserver(sync).observe(document.body,{childList:true,subtree:true});
})();</script>
HTML;
    $design=str_replace(['DEPTH_LABEL','RAISED_LABEL','FLAT_LABEL','NAV_LABEL','BACK_LABEL','FORWARD_LABEL','HOME_LABEL','MONITOR_LABEL','MOVE_LABEL','SETTINGS_LABEL','SETUP_LABEL'],array_map($esc,[
        $t('Térhatás','Depth','Tiefe'),$t('Térhatású kártyák','Raised cards','Erhabene Karten'),$t('Sík megjelenés','Flat appearance','Flache Darstellung'),
        $t('Mover navigáció','Mover navigation','Mover-Navigation'),$t('Vissza','Back','Zurück'),$t('Előre','Forward','Vorwärts'),$t('Főoldal','Home','Startseite'),
        $t('Mover figyelő','Monitor','Monitor'),$t('Mozgatás','Movement','Verschieben'),$t('Beállítások','Settings','Einstellungen'),$t('Mód és pool','Mode and pool','Modus und Pool')]),$design);
    $banner=str_replace('<strong>', $theme.'<strong>',$banner);
    // Dashboard polling keeps only .fmc-mode: carry the shared stylesheet with it.
    $designStyleEnd = strpos($design, '</style>') + strlen('</style>');
    $banner = substr_replace($banner, substr($design, 0, $designStyleEnd), strrpos($banner, '</div>'), 0);
    $banner .= substr($design, $designStyleEnd);
    $token = @parse_ini_file('/var/local/emhttp/var.ini');
    return ['mode'=>$mode,'pool'=>$pool,'path'=>'/mnt/'.$pool,'mounted'=>$mounted,'pools'=>$pools,
        'error'=>$error,'lockError'=>$lockError,'readError'=>$readError,'configInvalid'=>!$valid,
        'pathConfig'=>$configPath,'raw'=>$raw === false ? '' : $raw,
        'hash'=>hash('sha256',$raw === false ? '' : $raw),'lock'=>$lock,
        'token'=>is_array($token) ? ($token['csrf_token'] ?? '') : '',
        't'=>$t,'esc'=>$esc,'banner'=>$banner];
})(!empty($fmcConfigWrite));
