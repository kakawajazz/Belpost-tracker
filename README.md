Belpost tracker
===============

Requires python 2.7

Script makes request to <b>Belarusian post tracking service</b> then parses response and sends sms via sms.ru service if parcel status gets changed.

<i>Script works only with Belarusian post tracking service. <br>It provides tracking only for internal Belarusian parcels and for parcels sent to Belarus from outside.</i>

Script needs to be placed and run on web-server or your local machine with internet access.

For automation you can add a cron job for periodically runnig the script, for example type `crontab -e` in terminal and add a string with new job like `0 */1 * * * /system/path/to/python /path/to/script/tracker.py` — this will run tracker once an hour in 00 minutes.

Script needs no database, but stores parsed data on a disk — little files up to 5kB size. By default path to that files: `~/www/python/sms/tracks`.

1. In order to send sms you need to register on sms.ru — it's free. Sms.ru provides API and allows to send unlimited number of free text messages to your own cell number — exactly what you need to! Sign up and get <b>api_id</b> here: `http://online.sms.ru/?panel=api`.
2. After getting settings you should update you <b>settings</b> in `settings.py`: replace phone number and api_id to yours, change tracks storing path if needed. 
3. Here in `settings.py` fill the list of <b>tracking items</b>. Item example: `['CJ420541567US', 'Longboard deck', 'international'],`. Here `CJ420541567US` is your tracking number, `Longboard deck` — write something to simply identify the item, `international` — required field that shows type of parcel (may be `international` or `local`).
4. After updating settings save `settings.py` then upload all files to server and <b>run</b> `tracker.py`

<b>Please note</b> about dependencies. They are listed in top of `tracker.py` in import section.
