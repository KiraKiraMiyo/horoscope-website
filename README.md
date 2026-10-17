# horoscope-website
A Horoscope website

## Daily forecast publishing

All daily dates use `Asia/Phnom_Penh` (UTC+7).

The **Tomorrow Zodiac JSON** scheduled task prepares the next two calendar days:

- `tomorrow.json`: current Cambodia date + 1 day.
- `day_after_tomorrow.json`: current Cambodia date + 2 days, prepared in advance for midnight rotation.

Each file uses the existing version-1 bilingual `en` / `kh` schema with all twelve signs. Readings must be original for each sign/date, with natural everyday Khmer. Never fix a duplicated forecast by changing only its date. Reuse an already valid prepared forecast for the same date rather than rewriting it on every run. Publish the two prepared files together in one commit, using the current branch head to avoid overwriting concurrent changes.

At 00:07 Cambodia time, `.github/workflows/rotate_horoscope.yml` runs the tests and `scripts/rotate_horoscope.py`. The script validates every input before writing, then promotes:

1. The previous Today to Yesterday.
2. The prepared reading for the new date to Today.
3. The prepared second-day buffer to Tomorrow.

A repeat run is a no-op once Today and Tomorrow are correct. A missing/stale/duplicated buffer fails the workflow visibly and leaves the published files unchanged. If an old copy-only rotation has already duplicated Today into Tomorrow, the script can restore Tomorrow from a correctly dated buffer without changing Yesterday.

The script does not generate new prose or make paid API calls. The scheduled generation task must replenish the buffer before the following midnight. Keep the task's existing daily timing, native-Khmer quality checks, and GitHub access.

Run the regression checks with:

```sh
python -m unittest discover -s tests -v
```
