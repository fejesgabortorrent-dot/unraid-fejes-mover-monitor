<?php
/* Read-only summary. No network requests, scheduling, or mover control here. */
$statRead = static function(string $name) use ($fmc) {
    if (($fmc['mode']??'demo')==='demo') return null;
    $path='/boot/config/plugins/fejes.mover.monitor/'.$name;
    if (is_link($path) || !is_file($path) || filesize($path)>262144) return null;
    $data=@file_get_contents($path);
    return is_string($data) ? json_decode($data,true) : null;
};
$statLast=$statRead('selective-last.json');
$statAudit=$statRead('completed-seed-events.json');
$statHistory=$statRead('github-download-history.json');
$statCounter=$statRead('github-downloads.json');
$statRows=[];
if (is_array($statHistory) && count($statHistory)<=4000) {
    $previous='';
    foreach ($statHistory as $row) {
        if (!is_array($row) || !is_string($row['date']??null) || !preg_match('/^\d{4}-\d{2}-\d{2}$/D',$row['date']) || !is_int($row['total']??null) || $row['total']<0 || $row['date']<=$previous) { $statRows=[]; break; }
        $previous=$row['date']; $statRows[]=$row;
    }
}
$statRows=array_slice($statRows,-31);
$statTotal=$statRows ? end($statRows)['total'] : (is_array($statCounter)&&is_int($statCounter['total']??null)&&$statCounter['total']>=0?$statCounter['total']:null);
$statEvents=is_array($statAudit)&&($statAudit['version']??null)===1&&is_array($statAudit['events']??null)?array_slice($statAudit['events'],-5):[];
$statFiles=is_array($statLast)&&is_int($statLast['moved_files']??null)&&$statLast['moved_files']>=0?$statLast['moved_files']:null;
$statBytes=is_array($statLast)&&is_int($statLast['moved_bytes']??null)&&$statLast['moved_bytes']>=0?$statLast['moved_bytes']:null;
$statOrigin=['manual'=>$fmT('Kézi','Manual','Manuell'),'scheduled'=>$fmT('Ütemezett','Scheduled','Geplant'),'pilot'=>$fmT('Diagnosztikai','Diagnostic','Diagnose')];
?>
<details class="fm-card" id="fm-statistics">
<summary><?=$fmEsc($fmT('Statisztika','Statistics','Statistik'))?></summary>
<h3><?=$fmEsc($fmT('Utolsó szelektív futás','Last selective run','Letzter selektiver Lauf'))?></h3>
<?php if ($statFiles!==null && $statBytes!==null): ?>
<p><?=$fmEsc($fmT('Ellenőrzött fájlok','Verified files','Geprüfte Dateien'))?>: <strong><?=$fmEsc($statFiles)?></strong> · <?=$fmEsc(number_format($statBytes/1073741824,2))?> GiB</p>
<?php else: ?><p><?=$fmEsc($fmT('Nincs ellenőrizhető futási adat.','No verified run data available.','Keine geprüften Laufdaten verfügbar.'))?></p><?php endif ?>
<p><?=$fmEsc($fmT('A legutóbbi letöltés utáni futás indítása','Latest completed-download run origin','Startquelle des letzten Abschlusslaufs'))?>: <?=$fmEsc($statOrigin[$statAudit['origin']??'']??$fmT('Ismeretlen','Unknown','Unbekannt'))?></p>
<?php if($statEvents): ?><ul><?php foreach($statEvents as $event): if(!is_array($event))continue; $tm=$event['time']??null; $name=$event['event']??null; if(!is_numeric($tm)||!is_string($name)||!preg_match('/^[a-z_]{1,50}$/D',$name))continue; ?><li><?=$fmEsc(date('Y-m-d H:i',(int)$tm))?> · <?=$fmEsc($name)?><?php if(is_string($event['reason']??null)&&preg_match('/^[a-z0-9_]{1,80}$/D',$event['reason'])&&$event['reason']!=='none'): ?> · <?=$fmEsc($event['reason'])?><?php endif ?></li><?php endforeach ?></ul><?php endif ?>
<p class="fm-note"><?=$fmEsc($fmT('Csak a legutóbbi rendelkezésre álló jelentés és események; nem teljes 30 napos előzmény.','Only the latest available report and events; not a complete 30-day history.','Nur der letzte verfügbare Bericht und Ereignisse; kein vollständiger 30-Tage-Verlauf.'))?> <a href="/Tools/FejesMoverSelective#fms-last"><?=$fmEsc($fmT('Futási napló','Run log','Laufprotokoll'))?></a></p>
<h3><?=$fmEsc($fmT('GitHub-telepítő letöltései','GitHub installer downloads','GitHub-Installerdownloads'))?></h3>
<p><?=$fmEsc($fmT('Legutóbbi mért összesen','Last measured total','Zuletzt gemessene Gesamtzahl'))?>: <strong><?=$statTotal===null?$fmEsc($fmT('Nincs mérés','No measurement','Keine Messung')):$fmEsc($statTotal)?></strong></p>
<?php if(count($statRows)>1): $max=max(1,max(array_column($statRows,'total'))); $count=count($statRows);$points=[];foreach($statRows as $i=>$row){$points[]=number_format(10+($i*280/($count-1)),2,'.','').','.number_format(90-($row['total']*75/$max),2,'.','');} ?>
<svg viewBox="0 0 300 110" style="width:100%;max-width:700px;height:auto" role="img" aria-label="<?=$fmEsc($fmT('GitHub-letöltések időbeli alakulása','GitHub downloads over time','GitHub-Downloads im Zeitverlauf'))?>"><line x1="10" y1="90" x2="290" y2="90" stroke="currentColor" opacity=".3"/><polyline points="<?=$fmEsc(implode(' ',$points))?>" fill="none" stroke="#ef7d00" stroke-width="2"/></svg>
<p class="fm-note"><?=$fmEsc($statRows[0]['date'])?> – <?=$fmEsc(end($statRows)['date'])?> (UTC)</p>
<?php else: ?><p><?=$fmEsc($fmT('A grafikonhoz legalább két külön napi mérés szükséges.','At least two daily observations are needed for the graph.','Für das Diagramm sind mindestens zwei tägliche Messungen nötig.'))?></p><?php endif ?>
<p class="fm-note"><?=$fmEsc($fmT('Csak a GitHub-kiadások telepítőfájljainak letöltései. Nem egyedi telepítések; a Community Applications és más források nem szerepelnek.','GitHub release installer assets only. Not unique installs; Community Applications and other sources are excluded.','Nur GitHub-Installationsdateien. Keine eindeutigen Installationen; Community Applications und andere Quellen fehlen.'))?></p>
</details>
