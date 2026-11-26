<?php
/* Read-only aggregate statistics. Never scan shares or query torrent clients here. */
$fmStatsRead=static function(string $path,int $max=2000000): mixed {
    if(is_link($path)||!is_file($path)||filesize($path)>$max)return null;
    $value=json_decode(@file_get_contents($path)?:'null',true);
    return json_last_error()===JSON_ERROR_NONE?$value:null;
};
$fmStatsText=[
 'hu'=>['title'=>'Statisztika','day'=>'Ma','week'=>'Utolsó 7 nap','month'=>'Utolsó 30 nap','runs'=>'Futások','files'=>'Mozgatott fájlok','data'=>'Mozgatott adatmennyiség','errors'=>'Hibák','empty'=>'Még nincs tartós futási előzmény. A következő szelektív futástól automatikusan gyűlik.','privacy'=>'Csak összesített adatok; fájlnevek és torrentazonosítók nem kerülnek az előzménybe.','downloads'=>'GitHub-telepítő letöltései','sample'=>'Napi minták','none'=>'Nincs mérés','latest'=>'Legutóbbi összesen'],
 'en'=>['title'=>'Statistics','day'=>'Today','week'=>'Last 7 days','month'=>'Last 30 days','runs'=>'Runs','files'=>'Files moved','data'=>'Data moved','errors'=>'Errors','empty'=>'No persistent run history yet. Collection starts automatically with the next selective run.','privacy'=>'Aggregate data only; file names and torrent identifiers are not stored in history.','downloads'=>'GitHub installer downloads','sample'=>'Daily samples','none'=>'No measurement','latest'=>'Latest total'],
 'de'=>['title'=>'Statistik','day'=>'Heute','week'=>'Letzte 7 Tage','month'=>'Letzte 30 Tage','runs'=>'Läufe','files'=>'Verschobene Dateien','data'=>'Verschobene Daten','errors'=>'Fehler','empty'=>'Noch kein dauerhafter Verlauf. Die Erfassung beginnt automatisch mit dem nächsten selektiven Lauf.','privacy'=>'Nur Summen; Dateinamen und Torrent-IDs werden nicht gespeichert.','downloads'=>'GitHub-Installer-Downloads','sample'=>'Tägliche Messwerte','none'=>'Keine Messung','latest'=>'Letzte Summe']
][$fmLang]??[];
$fmStatsRows=$fmStatsRead('/boot/config/plugins/fejes.mover.monitor/run-history.json');
$fmStatsRows=is_array($fmStatsRows)?array_values(array_filter($fmStatsRows,static fn($r)=>is_array($r)&&is_numeric($r['finished']??null)&&is_string($r['state']??null)&&is_numeric($r['moved_files']??null)&&is_numeric($r['moved_bytes']??null))):[];
$fmStatsNow=time();$fmStatsToday=strtotime('today');
$fmStatsSummarize=static function(array $rows,int $since): array {
    $out=['runs'=>0,'files'=>0,'bytes'=>0,'errors'=>0];
    foreach($rows as $row){if((float)$row['finished']<$since)continue;$out['runs']++;$out['files']+=max(0,(int)$row['moved_files']);$out['bytes']+=max(0,(int)$row['moved_bytes']);if($row['state']==='error')$out['errors']++;}
    return $out;
};
$fmStatsPeriods=[
 [$fmStatsText['day'],$fmStatsSummarize($fmStatsRows,$fmStatsToday)],
 [$fmStatsText['week'],$fmStatsSummarize($fmStatsRows,$fmStatsNow-7*86400)],
 [$fmStatsText['month'],$fmStatsSummarize($fmStatsRows,$fmStatsNow-30*86400)]
];
$fmStatsSize=static function(int $bytes): string {
    if($bytes<1073741824)return number_format($bytes/1048576,2,'.','').' MiB';
    return number_format($bytes/1073741824,2,'.','').' GiB';
};
$fmDownloadRows=$fmStatsRead('/boot/config/plugins/fejes.mover.monitor/github-download-history.json',1000000);
$fmDownloadRows=is_array($fmDownloadRows)?array_values(array_filter($fmDownloadRows,static fn($r)=>is_array($r)&&preg_match('/^\d{4}-\d{2}-\d{2}$/D',(string)($r['date']??''))&&is_int($r['total']??null)&&$r['total']>=0)):[];
$fmDownloadRows=array_slice($fmDownloadRows,-31);
$fmDownloadCurrent=$fmStatsRead('/boot/config/plugins/fejes.mover.monitor/github-downloads.json',100000);
$fmDownloadTotal=is_array($fmDownloadCurrent)&&is_int($fmDownloadCurrent['total']??null)?$fmDownloadCurrent['total']:($fmDownloadRows?end($fmDownloadRows)['total']:null);
?>
<style>
#fm-statistics{margin:18px 0 22px;padding:18px;border:1px solid #8885;border-radius:10px;background:#88808}#fm-statistics h3{margin:0 0 14px}.fm-stat-periods{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.fm-stat-period{padding:14px;border:1px solid #8884;border-top:3px solid #ef8b24;border-radius:8px}.fm-stat-period strong{display:block;font-size:17px;margin-bottom:8px}.fm-stat-period dl{display:grid;grid-template-columns:1fr auto;gap:5px;margin:0;font-size:13px}.fm-stat-period dd{margin:0;font-variant-numeric:tabular-nums}.fm-downloads{margin-top:14px;padding-top:14px;border-top:1px solid #8884}.fm-spark{display:flex;align-items:flex-end;gap:3px;height:54px;margin-top:8px}.fm-spark i{flex:1;min-width:3px;max-width:18px;background:#64b99b;border-radius:2px 2px 0 0}.fm-stat-note{font-size:12px;opacity:.75;margin:12px 0 0}@media(max-width:700px){.fm-stat-periods{grid-template-columns:1fr}}
</style>
<section id="fm-statistics" aria-label="<?=$fmEsc($fmStatsText['title'])?>"><h3><?=$fmEsc($fmStatsText['title'])?></h3>
<?php if($fmStatsRows):?><div class="fm-stat-periods"><?php foreach($fmStatsPeriods as [$fmPeriodLabel,$fmPeriod]):?><div class="fm-stat-period"><strong><?=$fmEsc($fmPeriodLabel)?></strong><dl><dt><?=$fmEsc($fmStatsText['runs'])?></dt><dd><?=$fmPeriod['runs']?></dd><dt><?=$fmEsc($fmStatsText['files'])?></dt><dd><?=$fmPeriod['files']?></dd><dt><?=$fmEsc($fmStatsText['data'])?></dt><dd><?=$fmEsc($fmStatsSize($fmPeriod['bytes']))?></dd><dt><?=$fmEsc($fmStatsText['errors'])?></dt><dd><?=$fmPeriod['errors']?></dd></dl></div><?php endforeach?></div><?php else:?><p><?=$fmEsc($fmStatsText['empty'])?></p><?php endif?>
<div class="fm-downloads"><strong><?=$fmEsc($fmStatsText['downloads'])?></strong><p><?=$fmEsc($fmStatsText['latest'])?>: <b><?=$fmDownloadTotal===null?$fmEsc($fmStatsText['none']):$fmDownloadTotal?></b> · <?=$fmEsc($fmStatsText['sample'])?>: <?=count($fmDownloadRows)?></p>
<?php if(count($fmDownloadRows)>1):$fmDownloadBase=$fmDownloadRows[0]['total'];$fmDownloadMax=max(1,max(array_column($fmDownloadRows,'total'))-$fmDownloadBase);?><div class="fm-spark" role="img" aria-label="<?=$fmEsc($fmStatsText['downloads'])?>"><?php foreach($fmDownloadRows as $fmDownloadRow):$fmDownloadHeight=8+46*(($fmDownloadRow['total']-$fmDownloadBase)/$fmDownloadMax);?><i style="height:<?=max(8,min(54,$fmDownloadHeight))?>px" title="<?=$fmEsc($fmDownloadRow['date'].' · '.$fmDownloadRow['total'])?>"></i><?php endforeach?></div><?php endif?></div>
<p class="fm-stat-note"><?=$fmEsc($fmStatsText['privacy'])?></p></section>
