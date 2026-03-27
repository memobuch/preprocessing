import logging


class FeatureAggregator:
    """

    """

    def __init__(self):
        """

        """
        pass

    def deduplicate_geojson_features(self, features: list[dict]) -> list[dict]:
        """
        Combine GeoJSON features with identical coordinates into multi-event features.
        Now handles exact duplicate events (same person, same location, same event type).
        """
        from collections import defaultdict

        # First pass: Remove exact duplicates (same person_id + coordinates + event_type)
        unique_features = {}
        duplicate_count = 0

        for feature in features:
            coords = feature['geometry']['coordinates']
            coord_key = (round(coords[0], 6), round(coords[1], 6))

            props = feature['properties']
            # Create unique key: person_id + coordinates + event_type
            unique_key = (
                props['person_id'],
                coord_key
                # props['event_type']
            )

            if unique_key in unique_features:
                duplicate_count += 1
                logging.warning(f"Removing exact duplicate feature: {unique_key}")
            else:
                unique_features[unique_key] = feature

        if duplicate_count > 0:
            logging.info(f"Removed {duplicate_count} exact duplicate features")

        # Second pass: Group remaining features by coordinates for clustering
        coord_groups = defaultdict(list)

        for feature in unique_features.values():
            coords = feature['geometry']['coordinates']
            coord_key = (round(coords[0], 6), round(coords[1], 6))
            coord_groups[coord_key].append(feature)

        # Third pass: Create combined features
        deduplicated_features = []

        for coord_key, group in coord_groups.items():
            if len(group) == 1:
                deduplicated_features.append(group[0])
            else:
                combined_feature = self._create_combined_feature(coord_key, group)
                deduplicated_features.append(combined_feature)

        return deduplicated_features

    def _create_combined_feature(self, coord_key: tuple, features: list[dict]) -> dict:
        """
        Create a single GeoJSON feature representing multiple events at the same location.

        Args:
            coord_key: (longitude, latitude) tuple
            features: List of feature dicts sharing this location

        Returns:
            Combined GeoJSON feature with event_type='multiple'
        """
        # Extract all individual events
        events = []
        all_person_ids = set()
        all_person_names = set()
        all_victim_categories = set()
        place_names = set()
        all_tags = set()

        for feature in features:
            props = feature['properties']

            # Collect event info
            event_info = {
                'person_id': props['person_id'],
                'person_name': props['person_name'],
                'tags': props['tags'],
                # 'event_type': props['event_type'],
                # 'event_type_label': props['event_type_label'],
                'place_name': props['place_name'],
                'date': props.get('date'),
                'event_id': props.get('event_id'),
                'event_title': props.get('event_title'),
                'event_description': props.get('event_description'),
                'birth_date': props.get('birth_date'),
                'death_date': props.get('death_date'),
                'gender': props.get('gender'),
                'is_youth': props.get('is_youth')
            }
            events.append(event_info)

            # Aggregate metadata
            all_person_ids.add(props['person_id'])
            all_person_names.add(props['person_name'])
            place_names.add(props['place_name'])

            # aggregate tags
            all_tags.update(props['tags'])

            if props.get('victim_categories'):
                all_victim_categories.update(props['victim_categories'])

        # Count event types
        # event_type_counts = {}
        # for event in events:
        #     event_type = event['event_type']
        #     event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        # Use most common place name (or first if tied)
        primary_place_name = max(place_names, key=lambda x: sum(1 for e in events if e['place_name'] == x))

        # Create combined feature
        combined_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [coord_key[0], coord_key[1]]
            },
            "properties": {
                # Mark as multiple events
                # "event_type": "multiple",
                # "event_type_label": "Mehrere Ereignisse",

                # tags
                "tags": sorted(list(all_tags)),

                # Summary statistics
                # "event_count": len(events),
                # "person_count": len(all_person_ids),
                # "event_type_counts": event_type_counts,

                # Location info
                # "place_name": primary_place_name,
                # "place_name_variants": list(place_names),

                # Aggregated person data
                # "person_ids": sorted(list(all_person_ids)),
                # "person_names": sorted(list(all_person_names)),
                # "victim_categories": sorted(list(all_victim_categories)),

                # Individual events (CRITICAL - preserves all data)
                "events": events,
            }
        }

        return combined_feature