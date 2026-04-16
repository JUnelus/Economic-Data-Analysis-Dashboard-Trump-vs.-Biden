SELECT indicator,
	   presidency,
	   MIN(observation_date) AS first_observation,
	   MAX(observation_date) AS latest_observation,
	   COUNT(*) AS observations
FROM economic_data
GROUP BY indicator, presidency
ORDER BY indicator, MIN(term_start);

SELECT indicator,
	   presidency,
	   MAX(value) FILTER (WHERE observation_date = latest_observation.latest_date) AS latest_value,
	   MAX(indexed_to_start) FILTER (WHERE observation_date = latest_observation.latest_date) AS latest_indexed_value
FROM economic_data data
JOIN (
	SELECT indicator_key,
		   presidency_key,
		   MAX(observation_date) AS latest_date
	FROM economic_data
	GROUP BY indicator_key, presidency_key
) latest_observation
  ON data.indicator_key = latest_observation.indicator_key
 AND data.presidency_key = latest_observation.presidency_key
 AND data.observation_date = latest_observation.latest_date
GROUP BY indicator, presidency
ORDER BY indicator, MIN(term_start);
