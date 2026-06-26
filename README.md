**Prediction Agent**
The prediction agent takes tracks from the "Tracking Agent" and predict where the drone is going to be in next N seconds.
We build in three levels; Kalman Filter, LSTM and Transformer based trajectory prediction.

We calculate the metrics in two ways; ADE (Average Displacement Error) and FDE (Final Displacement Error).
**Average displacement Erro**r is the avg distance between actual and predicted position across all timestamps.
**Final displacement Error** is the distance between actual and predicted position at the final timestamp only.

**FINAL MODEL METRICS**

| Model name | ADE | FDE |
| --- | --- | --- |
|Kalman Filter| 2.4213 | 3.9685 | 
|LSTM| 2.7209 | 4.1753 | 
|Transformer|  2.6791 | 4.0752 | 
|Social Force|  1.9569 | 3.2349 | 
