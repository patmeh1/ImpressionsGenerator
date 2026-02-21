import {
  PublicClientApplication,
  Configuration,
  LogLevel,
  AccountInfo,
  SilentRequest,
  RedirectRequest,
} from '@azure/msal-browser';

const msalConfig: Configuration = {
  auth: {
    clientId: process.env.NEXT_PUBLIC_AZURE_CLIENT_ID || '',
    authority: `https://login.microsoftonline.com/${process.env.NEXT_PUBLIC_AZURE_TENANT_ID || 'common'}`,
    redirectUri: process.env.NEXT_PUBLIC_REDIRECT_URI || 'http://localhost:3000',
    postLogoutRedirectUri: '/',
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return;
        switch (level) {
          case LogLevel.Error:
            console.error(message);
            break;
          case LogLevel.Warning:
            console.warn(message);
            break;
        }
      },
      logLevel: LogLevel.Warning,
    },
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

export const loginScopes = {
  scopes: [
    `api://${process.env.NEXT_PUBLIC_AZURE_CLIENT_ID}/access_as_user`,
  ],
};

export async function loginRedirect(): Promise<void> {
  const request: RedirectRequest = { ...loginScopes };
  await msalInstance.loginRedirect(request);
}

export async function loginPopup(): Promise<AccountInfo | null> {
  try {
    const response = await msalInstance.loginPopup(loginScopes);
    return response.account;
  } catch (error) {
    console.error('Login failed:', error);
    return null;
  }
}

export async function logout(): Promise<void> {
  await msalInstance.logoutRedirect();
}

export async function getAccessToken(): Promise<string | null> {
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length === 0) return null;

  const request: SilentRequest = {
    ...loginScopes,
    account: accounts[0],
  };

  try {
    const response = await msalInstance.acquireTokenSilent(request);
    return response.accessToken;
  } catch (error) {
    try {
      const response = await msalInstance.acquireTokenPopup(loginScopes);
      return response.accessToken;
    } catch (popupError) {
      console.error('Token acquisition failed:', popupError);
      return null;
    }
  }
}

export function getActiveAccount(): AccountInfo | null {
  const accounts = msalInstance.getAllAccounts();
  return accounts.length > 0 ? accounts[0] : null;
}
