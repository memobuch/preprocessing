from memorbuch_preprocessing.MemorProcessor import MemorProcessor


def main():
    memor_processor = MemorProcessor()
    memor_processor.load_data()
    memor_processor.output_data()
    memor_processor.output_person_list_object()