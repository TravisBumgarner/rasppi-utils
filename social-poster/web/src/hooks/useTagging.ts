import { useMutation } from '@tanstack/react-query';
import { generateCaptions } from '../api/client';
import type { TaggingPreview } from '../api/types';

/** Run the tagging script on a chosen photo to pre-fill caption fields. */
export function useGenerateCaptions() {
  return useMutation<TaggingPreview, Error, File>({
    mutationFn: generateCaptions,
  });
}
