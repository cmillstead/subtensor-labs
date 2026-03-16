import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { ENGINE_URL } from "./constants";

declare module "next-auth" {
  interface Session {
    user: DefaultSession["user"] & { premiumStatus: string };
  }
  interface User {
    premiumStatus: string;
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    id: string;
    premiumStatus: string;
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { type: "email" },
        password: { type: "password" },
      },
      authorize: async (credentials) => {
        const { email, password } = credentials as {
          email: string;
          password: string;
        };

        let res: Response;
        try {
          res = await fetch(`${ENGINE_URL}/engine/users/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          });
        } catch {
          // Engine unreachable — return null to show generic auth failure
          return null;
        }

        if (!res.ok) return null;

        const body = await res.json();
        const user = body.data;

        return {
          id: String(user.id),
          email: user.email,
          premiumStatus: user.premium_status,
        };
      },
    }),
  ],

  session: {
    strategy: "jwt",
    maxAge: 15 * 60, // 15 minutes
  },

  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.id = user.id!;
        token.premiumStatus = user.premiumStatus;
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        session.user.id = token.id;
        session.user.premiumStatus = token.premiumStatus;
      }
      return session;
    },
  },

  pages: {
    signIn: "/auth/login",
  },
});
