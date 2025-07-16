query_str = '''
WITH

b AS (
  SELECT
    id,
    download_link,
    profile_username,
    post_url,
    posted_at,
    derived_impressions,
    profile_followers_count,
    CASE
      WHEN profile_followers_count < 10000   THEN '<10k'
      WHEN profile_followers_count < 50000   THEN '10k-50k'
      WHEN profile_followers_count < 200000  THEN '50k-200k'
      WHEN profile_followers_count < 800000  THEN '200k-800k'
      ELSE '800k+'
    END AS tier
  FROM `insider-lake-sensitive.unfolded_br.unfolded__mighty_scout_campaign_media`
  WHERE 1=1
    AND posted_at >= '2024-12-01'
    AND is_video
    AND is_reel
    AND profile_username NOT LIKE '%jhoonrb%'
    AND profile_username NOT LIKE '%insider%'
    AND download_link IS NOT NULL
    AND NOT LOWER(active_labels) LIKE '%opt_out_mkt%'
),

median_per_tier AS (
  SELECT
    tier,
    APPROX_QUANTILES(derived_impressions, 100)[OFFSET(50)] AS median_impr
  FROM b
  GROUP BY tier
),

gsheets AS (
  SELECT
    post_url,
    outcome
  FROM `insider-lake-sensitive.landing_br.gsheets_influencer_creative_video_approval`
)

SELECT
    b.id,
    b.download_link,
    b.profile_username,
    b.post_url,
    b.posted_at,
    gsheets.outcome,
    (b.derived_impressions / m.median_impr - 1) AS delta_from_median
FROM b
JOIN median_per_tier AS m
  ON b.tier = m.tier
LEFT JOIN gsheets
  USING (post_url)
WHERE 1=1
  -- só quem passou da mediana do seu tier
  -- AND (b.derived_impressions >= m.median_impr OR profile_followers_count > 30000)
  -- sem outcome já avaliado
  AND gsheets.outcome IS NULL
ORDER BY
  b.posted_at DESC
'''
