CREATE TABLE public.topic_progress (
  user_id uuid NOT NULL DEFAULT auth.uid(),
  topic text NOT NULL,
  score integer NOT NULL DEFAULT 0 CHECK (score BETWEEN 0 AND 100),
  correct_count integer NOT NULL DEFAULT 0,
  wrong_count integer NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, topic)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.topic_progress TO authenticated;
GRANT ALL ON public.topic_progress TO service_role;
ALTER TABLE public.topic_progress ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Own progress read" ON public.topic_progress FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Own progress insert" ON public.topic_progress FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Own progress update" ON public.topic_progress FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Own progress delete" ON public.topic_progress FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- +10 for a correct answer, -5 for a wrong one, kept between 0 and 100.
CREATE OR REPLACE FUNCTION public.record_answer(_topic text, _correct boolean)
RETURNS public.topic_progress
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE r public.topic_progress;
BEGIN
  IF auth.uid() IS NULL THEN RAISE EXCEPTION 'Not signed in'; END IF;
  INSERT INTO public.topic_progress AS tp (user_id, topic, score, correct_count, wrong_count)
  VALUES (auth.uid(), _topic, CASE WHEN _correct THEN 10 ELSE 0 END,
          CASE WHEN _correct THEN 1 ELSE 0 END, CASE WHEN _correct THEN 0 ELSE 1 END)
  ON CONFLICT (user_id, topic) DO UPDATE SET
    score = LEAST(100, GREATEST(0, tp.score + CASE WHEN _correct THEN 10 ELSE -5 END)),
    correct_count = tp.correct_count + CASE WHEN _correct THEN 1 ELSE 0 END,
    wrong_count = tp.wrong_count + CASE WHEN _correct THEN 0 ELSE 1 END,
    updated_at = now()
  RETURNING * INTO r;
  RETURN r;
END $$;
REVOKE EXECUTE ON FUNCTION public.record_answer(text, boolean) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.record_answer(text, boolean) TO authenticated;