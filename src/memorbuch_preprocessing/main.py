from memorbuch_preprocessing.MemorProcessor import MemorProcessor


def main():
    memo_processor = MemorProcessor()
    memo_processor.load_data()
    memo_processor.output_data()
    memo_processor.output_person_list_object()