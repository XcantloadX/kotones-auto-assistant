import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("tasks", "routes/tasks.tsx"),
  route("settings", "routes/settings.tsx"),
  route("produce", "routes/produce.tsx"),
  route("feedback", "routes/feedback.tsx"),
  route("update", "routes/update.tsx"),
  route("screen", "routes/screen.tsx"),
] satisfies RouteConfig;
