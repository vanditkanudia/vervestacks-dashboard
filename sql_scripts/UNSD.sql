SELECT 
	T1.*
	FROM [UNSD].[dbo].[DF_UNDATA_ENERGY_Statistics_n_Balance] T1
	inner join [UNSD].[dbo].unsd_product_map T2 ON T1.COMMODITY=iif(len(T2.code)=3,'0','') + try_convert(nvarchar,T2.Code)
	inner join [UNSD].[dbo].unsd_flow_map T3 ON T1.[TRANSACTION]=T3.Code
	inner join [UNSD].[dbo].unsd_region_map T4 ON T1.[REF_AREA]=T4.Code AND not T4.ISO = 'N/A'
  where not sub_total =1
  --AND T4.ISO='USA'
  --AND TIME_PERIOD='2022'
  and sector in ('Power','Industry','Residential','Services','Agriculture','Other','Energy','imports','exports')
  --and sector in ('Power')
  and attribute in ('transformation','consumption','import','export')
  --and attribute in ('transformation')
  and not fuel_agg is null


  --group by T3.[Desc],T2.fuel,T2.fuel_Agg,T3.attribute,T3.sector,T3.sub_sector,TIME_PERIOD
  
