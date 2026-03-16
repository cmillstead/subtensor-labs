export { auth as middleware } from "@/lib/auth";

export const config = {
  matcher: ["/dashboard/:path*", "/predictions/:path*", "/alerts/:path*", "/settings/:path*"],
};
