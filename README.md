# YouTube Harvester

A small Go CLI that turns a YouTube video into one readable text report.

<p align="center">
  <img src="asset/1.png" width="86%" alt="YouTube Harvester report header and metadata">
</p>

The report keeps video metadata, a timestamped transcript, root comments, and their replies together.

<table>
  <tr>
    <td><img src="asset/2.png" alt="Timestamped transcript output"></td>
    <td><img src="asset/3.png" alt="Threaded comment output"></td>
  </tr>
</table>

Manual English subtitles come first.
Automatic English captions are the fallback.
If neither exists, the report says so plainly.

[Install, run, and inspect the extraction limits](GUIDE.md).
