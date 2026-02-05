import time
from app.config import SIZE_CHART_MALE, SIZE_CHART_FEMALE


def recommend_size(measurements, size_chart):
    """
    Recommends a size based on body measurements and size chart.
    
    Logic: Finds the smallest size where ALL measurements fit (all <= size limits).
    """
    rec_start_time = time.time()
    
    if not measurements or "measurements_cm" not in measurements:
        return None
    
    meas = measurements["measurements_cm"]
    shoulder = meas.get("shoulder_width", {}).get("value", 0)
    chest = meas.get("chest_circumference", {}).get("value", 0)
    waist = meas.get("waist_circumference", {}).get("value", 0)
    
    size_order = list(size_chart.keys())
    checked_sizes = []
    
    for i, size in enumerate(size_order):
        size_measurements = size_chart[size]
        
        shoulder_fits = shoulder <= size_measurements.get("shoulder", float('inf'))
        chest_fits = chest <= size_measurements.get("chest", float('inf'))
        waist_fits = waist <= size_measurements.get("waist", float('inf'))
        
        reasons = []
        if not shoulder_fits:
            reasons.append(f"shoulder ({shoulder:.1f} > {size_measurements.get('shoulder', 0):.1f})")
        if not chest_fits:
            reasons.append(f"chest ({chest:.1f} > {size_measurements.get('chest', 0):.1f})")
        if not waist_fits:
            reasons.append(f"waist ({waist:.1f} > {size_measurements.get('waist', 0):.1f})")
        
        checked_sizes.append({
            "size": size,
            "fits": shoulder_fits and chest_fits and waist_fits,
            "reasons": reasons if reasons else ["All measurements fit"]
        })
        
        if shoulder_fits and chest_fits and waist_fits:
            rec_end_time = time.time()
            rec_latency = rec_end_time - rec_start_time
            return {
                "recommended_size": size,
                "reason": "All measurements fit within this size",
                "checked_sizes": checked_sizes,
                "recommendation_time_seconds": round(rec_latency, 6),
                "comparison": {
                    "shoulder": {
                        "measured": shoulder,
                        "size_limit": size_measurements.get("shoulder"),
                        "fits": shoulder_fits
                    },
                    "chest": {
                        "measured": chest,
                        "size_limit": size_measurements.get("chest"),
                        "fits": chest_fits
                    },
                    "waist": {
                        "measured": waist,
                        "size_limit": size_measurements.get("waist"),
                        "fits": waist_fits
                    }
                }
            }
        
        if i == len(size_order) - 1:
            rec_end_time = time.time()
            rec_latency = rec_end_time - rec_start_time
            return {
                "recommended_size": size,
                "reason": "Measurements exceed largest available size - recommending largest size",
                "checked_sizes": checked_sizes,
                "recommendation_time_seconds": round(rec_latency, 6),
                "comparison": {
                    "shoulder": {
                        "measured": shoulder,
                        "size_limit": size_measurements.get("shoulder"),
                        "fits": shoulder_fits
                    },
                    "chest": {
                        "measured": chest,
                        "size_limit": size_measurements.get("chest"),
                        "fits": chest_fits
                    },
                    "waist": {
                        "measured": waist,
                        "size_limit": size_measurements.get("waist"),
                        "fits": waist_fits
                    }
                }
            }
    
    rec_end_time = time.time()
    rec_latency = rec_end_time - rec_start_time
    return {
        "recommended_size": size_order[-1],
        "reason": "Could not determine fit, recommending largest size",
        "checked_sizes": checked_sizes,
        "recommendation_time_seconds": round(rec_latency, 6),
        "comparison": {}
    }


def get_size_chart_by_gender(gender):
    """Get the appropriate size chart based on gender."""
    gender_lower = gender.lower() if gender else ""
    if "female" in gender_lower:
        return SIZE_CHART_FEMALE, "Female"
    return SIZE_CHART_MALE, "Male"

