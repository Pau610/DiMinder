import pandas as pd
from datetime import datetime
import re

# Read the data file
data_lines = """Date	Time	Blood Glucose (mmol)	Long-acting (u)	Short-acting (u)	Timing	Carbs (g)	Food Items
15/6	01:50	10.9	–	3	↓ Post-check	–	–
15/6	12:45	–	22	–	↑ Basal	–	–
15/6	14:25	–	–	15	↑ Pre-meal	55	燒賣 排骨豆卜 牛肉球 三絲炆米粉(20) 蝦腸粉(5) 奶黃包(10) 珍珠奶茶(20)
15/6	19:15	–	–	10	↑ Pre-meal	25	泡菜 牛肉 牛舌 韭菜餃 魚腐 豆腐 洋蔥 金菇 蒟蒻 娃娃菜 (25)
14/6	01:25	5.7	–	–	–	–	–
14/6	14:45	–	22	–	↑ Basal	–	–
14/6	14:45	–	–	17	↑ Pre-meal	85	黑咖啡 麵包沙律(5) 牛油果牛肉炸魚柳漢堡(25) 薯條(25) 榴槤雪糕巴斯克芝士蛋糕(30)
14/6	19:55	7.8	–	–	–	–	–
14/6	19:55	–	–	10	↓ Post-check	60	三文魚 帶子 甜蝦 刺身壽司(10) BBQ烤肉薄餅(20) 牛扒羊架 薯條(20) 冬瓜瑤柱瘦肉湯 焦糖年輪蛋糕(10)
13/6	00:05	3.5	–	–	–	–	–
13/6	08:15	–	22	–	↑ Basal	–	–
13/6	14:20	–	–	7	↑ Pre-meal	35	Chia酒釀黑芝麻豆漿(10) 牛油果 車厘茄藍莓(5) 榛子巧克力餅櫻花蝦曲奇(20) 湯
13/6	20:15	3.9	–	–	–	–	–
13/6	20:15	–	–	6	↓ Post-check	5	咖哩薯仔雞翼 魚糕 腐皮卷 腸仔 韭菜餃 油麥菜 豬肉湯 奶酪紅棗果仁(5) 紫菜脆脆
12/6	08:05	–	23	–	↑ Basal	–	–
12/6	13:00	–	–	7	↑ Pre-meal	38	Chia酒釀黑芝麻豆漿(10) 櫻花蝦曲奇(10) 黑芝麻花生糖(5) 牛油果0.5 烚蛋1 車厘茄藍莓(10) 紫菜肉鬆小貝(3)
12/6	19:30	–	–	4	↑ Pre-meal	20	炸雞髀 燒雞髀 辣薯條(20)
12/6	21:20	–	–	5	↑ Pre-meal	–	咖喱薯仔雞肉 苦瓜 菜心 湯
11/6	00:30	3.3	–	–	–	20	榴槤荔枝(10) kitkat(10)
11/6	12:30	–	23	–	↑ Basal	–	–
11/6	14:30	–	–	10	↑ Pre-meal	40	鮮奶咖啡(10) 牛油果 車厘茄藍莓(10) 紫菜肉鬆小貝(10) 杏仁巧克力餅(10)
11/6	20:00	–	–	7	↑ Pre-meal	15	南瓜排骨(15) 三文魚 菜心 紅蘿蔔苦瓜淡菜豬肉湯
11/6	23:40	3.1	–	–	–	20	香蔥牛扎餅(10) 合桃酥(10)
10/6	01:30	5.4	–	–	–	–	–
10/6	09:10	–	23	–	↑ Basal	–	–
10/6	09:10	–	–	8	↑ Pre-meal	35	椰香奶酥麵包(30) 茉香奶油蛋糕(5)
10/6	13:10	–	–	11	↑ Pre-meal	35	魚翅魚肚羹 乳豬 豉油蔥油雞 扇貝粉絲(5) 蒸魚 蒸蝦 牛筋冬菇菜豬肉粒蘑菇 車厘茄火龍果番石榴(10) 紅豆沙(20)
10/6	19:10	–	–	14	↑ Pre-meal	55	芋頭椰子雞鍋(牛雞肉豬肚 丸魚腐豆腐生菜麵)(20) 椰子奶凍(15) 莓果啫喱芝士蛋糕(20)
9/6	01:15	4.1	-	-	-	-	-
9/6	12:10	-	23	-	↑ Basal	-	-
9/6	13:15	-	-	17	↑ Pre-meal	40	豆奶香料奶茶(20) 燒賣 菜苗餃 鮮竹卷 鳳爪 炸蘿蔔絲腸粉(10) 叉燒包(5) 鹹水角 奶酪紅棗果仁(5)
9/6	19:50	-	-	-	-	15	三文魚沙律飯團(15)
9/6	21:55	-	-	13	↑ Pre-meal	40	豆漿油條(20) 香腸 餃子 小籠包 生煎包 雞蛋瘦肉腸粉(10) 牛肉炒河粉米粉(10)
8/6	02:45	12.1	-	4	↓ Post-check	-	-
8/6	13:00	6.8	23	-	↑ Basal	-	-
8/6	14:50	-	-	14	↑ Pre-meal	45	開心果芥末合桃包(20) 火鍋(牛肉牛丸 豆腐菜河粉)(10) 奶香芒果紅棗合桃(15)
8/6	19:35	-	-	5	↑ Pre-meal	20	薑汁撞奶雙皮奶(20)
8/6	21:55	-	-	13	↑ Pre-meal	50	飯(10) 粉絲蝦煲(20) 炸蝦餅 燒雞 魚香茄子 雲呢拿雪糕多士(20)
7/6	10:35	-	23	-	↑ Basal	-	-
7/6	13:00	-	-	18	↑ Pre-meal	80	麥片麵包(5) 蝦餃 菜苗餃 蝦春卷(10) 蝦腸粉(10) 南瓜粥(10) 叉燒餐包(5) 蓮子馬蹄西米露(10) 榴槤雞蛋布丁(15) 紫薯鮮奶(15) 鹹蛋黃肉鬆糯米糍(10) 香腸
7/6	19:10	-	-	13	↑ Pre-meal	50	蘑菇忌廉湯 芒果蟹柳沙律 炸魷魚鬚 啫啫雞 斑蘭多士(5) 牛扒菠蘿五花肉 黑松露意粉(15) 巧克力芝士蛋糕提拉米蘇(15) 開心果花生芝麻糯米糍(10)
6/6	01:20	4.1	-	-	-	-	-
6/6	08:05	-	23	-	↑ Basal	-	-
6/6	14:50	-	-	8	↑ Pre-meal	17	黑咖啡 藍莓車厘茄(10)青瓜 Chia choco nut bar(7)
6/6	19:40	-	-	12	↑ Pre-meal	10	炸雞上髀 下髀 (10)
6/6	23:45	4.1	-	-	-	8	榴槤(5) 辣豬肉脆條(3)
5/6	00:30	3.6	-	-	-	5	奶酪紅棗果仁(5)
5/6	08:20	-	23	-	↑ Basal	-	-
5/6	12:15	-	-	8	↑ Pre-meal	32	可可咖啡 烚蛋1 藍莓車厘茄(5) 醃青瓜(5) 開心果巧克力(10) Chia choco nut bar(7)
5/6	19:10	-	-	20	↑ Pre-meal	33	燒烤(牛肉牛肋條牛舌雞翼雞扒) 火鍋(牛豬肉金菇生菜娃娃菜) 吉列豬扒炸蝦炸魚柳炸雞 燒鰻魚蝦片鵝肝(3) 鯛魚燒棉花糖椰子流心球(15) 牛奶咖啡雪條(15) 墨魚湯
4/6	08:00	-	23	2	↑ Basal	10	Chia酒釀黑芝麻豆漿(10)
4/6	13:15	-	-	5	↑ Pre-meal	20	鮮奶咖啡(10) 牛油果 藍莓車厘茄(5) 醃青瓜(5)
4/6	19:05	-	-	14	↑ Pre-meal	25	魷魚串燒 牛肉串燒 豬肉串燒 蘆筍卷串燒 雞腎串燒 雞軟骨串燒 焦糖菠蘿鵝肝多士 大蝦墨魚滑紫菜卷 炸九肚魚(25)
3/6	01:00	3.7	-	-	-	10	花生糯米糍(10)
3/6	08:05	-	23	-	↑ Basal	-	-
3/6	13:00	-	-	9	↑ Pre-meal	20	花生糯米糍(15) 烚蛋 牛油果 藍莓車厘茄 青瓜(5)
3/6	20:30	-	-	-	-	20	齋滷味 叉燒炒蛋 蝦醬通菜 螺片湯 黃豆粉蕨餅(10) 夏威夷果仁巧克力(5) 奇異果(5)
3/6	23:50	8.1	-	1	↓ Post-check	-	-
2/6	00:25	12.3	-	4	↓ Post-check	-	-
2/6	08:15	-	23	-	↑ Basal	-	-
2/6	12:10	-	-	8	↑ Pre-meal	35	鮮奶咖啡(5) 雞批(15) 烚蛋1 藍莓車厘茄(5) 青瓜1 榛子開心果巧克力(10)
2/6	20:30	10.2	-	-	-	-	-
2/6	20:30	-	-	11	↓ Post-check	13	叉燒燒肉 滷水鴨 齋滷味 蒸魚 菜心 湯 榴槤(3) 花生糯米糍(10)
1/6	10:45	-	23	-	↑ Basal	-	-
1/6	11:15	-	-	17	↑ Pre-meal	42	抹茶鮮奶(10) 雞肉牛油果沙律 煙三文魚 黑松露炒蛋 蘑菇 西蘭花 番茄 無花果乾麵包(2) 乳酪果仁脆脆(10) 松子糯米糕(20)
1/6	17:30	-	-	-	-	20	草莓豆奶檸檬茶(20)
1/6	19:30	-	-	8	↑ Pre-meal	25	牛肉 豬肉 雞肉 魚片 蝦 丸 腸仔 韭菜餃 豆腐 金菇 油麥菜 生菜 炸魚皮 (25)"""

# Parse the data
lines = data_lines.strip().split('\n')
header = lines[0].split('\t')

processed_data = []

for line in lines[1:]:
    cols = line.split('\t')
    if len(cols) >= 8:
        date_str = cols[0]
        time_str = cols[1]
        glucose_mmol = cols[2]
        long_acting = cols[3]
        short_acting = cols[4]
        timing = cols[5]
        carbs = cols[6]
        food_items = cols[7]
        
        # Parse date and time
        if date_str and time_str:
            try:
                # Convert DD/M to 2024-MM-DD format
                day, month = date_str.split('/')
                datetime_str = f"2024-{int(month):02d}-{int(day):02d} {time_str}"
                timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                
                # Convert glucose from mmol/L to mg/dL (multiply by 18.0182)
                glucose_level = 0
                if glucose_mmol and glucose_mmol not in ['-', '–']:
                    glucose_level = float(glucose_mmol) * 18.0182
                
                # Parse insulin
                insulin_dose = 0
                insulin_type = ""
                if long_acting and long_acting not in ['-', '–']:
                    insulin_dose = float(long_acting)
                    insulin_type = "长效胰岛素"
                elif short_acting and short_acting not in ['-', '–']:
                    insulin_dose = float(short_acting)
                    insulin_type = "短效胰岛素"
                
                # Parse carbs
                carbs_amount = 0
                if carbs and carbs not in ['-', '–']:
                    carbs_amount = float(carbs)
                
                # Parse food items
                food_details = ""
                if food_items and food_items not in ['-', '–']:
                    food_details = food_items
                
                # Create record
                record = {
                    'timestamp': timestamp,
                    'glucose_level': glucose_level,
                    'carbs': carbs_amount,
                    'insulin': insulin_dose,
                    'insulin_type': insulin_type,
                    'injection_site': '',
                    'food_details': food_details
                }
                
                processed_data.append(record)
                
            except Exception as e:
                print(f"Error processing line: {line}")
                print(f"Error: {e}")

# Create DataFrame
df = pd.DataFrame(processed_data)
df = df.sort_values('timestamp')

print(f"Processed {len(df)} records")
print("\nSample records:")
print(df.head(10).to_string())

# Save to CSV for import
df.to_csv('processed_dm_data.csv', index=False)
print("\nData saved to processed_dm_data.csv")