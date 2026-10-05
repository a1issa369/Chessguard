import { lazy, Suspense } from "react";
import App from "./App";
import NotFound from "./pages/NotFound";
import useTheme from "./hooks/useTheme";
import { usePath } from "./router";

// Legal pages are rarely visited, so they load as separate chunks and stay
// out of the main bundle.
const Privacy = lazy(() => import("./pages/Privacy"));
const Terms = lazy(() => import("./pages/Terms"));

export default function Root() {
  const path = usePath();
  const [theme, setTheme] = useTheme();
  const shared = { theme, onThemeChange: setTheme };

  let page;
  if (path === "/") page = <App {...shared} />;
  else if (path === "/privacy") page = <Privacy {...shared} />;
  else if (path === "/terms") page = <Terms {...shared} />;
  else page = <NotFound {...shared} />;

  return (
    <>
      <Suspense fallback={null}>{page}</Suspense>
    </>
  );
}
