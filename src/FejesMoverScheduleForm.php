<form method="post" action="/Tools/FejesMoverAutomation">
<input type="hidden" name="fmc_csrf" value="<?=$esc($runtime['token']??'')?>">
<p><label><input type="checkbox" name="enabled" value="1" <?=($data['enabled']??false)===true?'checked':''?>> <?=$esc($t('Automatikus mozgatás engedélyezése','Enable automatic movement','Automatische Bewegung aktivieren'))?></label></p>
<?php foreach(['threshold_gib'=>[$t('Szabadhely-küszöb (GiB)','Free space threshold (GiB)','Freier Speicher: Schwelle (GiB)'),300,1048576],'cooldown_minutes'=>[$t('Két kör között (perc)','Between batches (minutes)','Zwischen Durchläufen (Minuten)'),60,10080]] as $key=>$v):?>
<p><label><?=$esc($v[0])?><br><input type="number" name="<?=$key?>" min="1" max="<?=$v[2]?>" required value="<?=$esc($data[$key]??$v[1])?>"></label></p>
<?php endforeach?>
<p><label><?=$esc($t('Ellenőrzés időköze (perc)','Check interval (minutes)','Prüfintervall (Minuten)'))?> <select name="interval_minutes"><?php foreach([5,10,15,30] as $n):?><option value="<?=$n?>" <?=($data['interval_minutes']??15)===$n?'selected':''?>><?=$n?></option><?php endforeach?></select></label></p>
<button type="submit"><?=$esc($t('Ütemezés mentése','Save schedule','Zeitplan speichern'))?></button>
</form>
