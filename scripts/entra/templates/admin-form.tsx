/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { isEmpty } from "lodash-es";
import Link from "next/link";
import { useForm } from "react-hook-form";
// plane internal packages
import { API_BASE_URL } from "@plane/constants";
import { Button, getButtonStyling } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IFormattedInstanceConfiguration, TInstanceMicrosoftAuthenticationConfigurationKeys } from "@plane/types";
// components
import { CodeBlock } from "@/components/common/code-block";
import { ConfirmDiscardModal } from "@/components/common/confirm-discard-modal";
import type { TControllerInputFormField } from "@/components/common/controller-input";
import { ControllerInput } from "@/components/common/controller-input";
import type { TControllerSwitchFormField } from "@/components/common/controller-switch";
import { ControllerSwitch } from "@/components/common/controller-switch";
import type { TCopyField } from "@/components/common/copy-field";
import { CopyField } from "@/components/common/copy-field";
// hooks
import { useInstance } from "@/hooks/store";

type Props = {
  config: IFormattedInstanceConfiguration;
};

type MicrosoftConfigFormValues = Record<TInstanceMicrosoftAuthenticationConfigurationKeys, string>;

const MICROSOFT_FORM_SWITCH_FIELD: TControllerSwitchFormField<MicrosoftConfigFormValues> = {
  name: "ENABLE_MICROSOFT_SYNC",
  label: "Microsoft",
};

export function InstanceMicrosoftConfigForm(props: Props) {
  const { config } = props;
  // states
  const [isDiscardChangesModalOpen, setIsDiscardChangesModalOpen] = useState(false);
  // store hooks
  const { updateInstanceConfigurations } = useInstance();
  // form data
  const {
    handleSubmit,
    control,
    reset,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<MicrosoftConfigFormValues>({
    defaultValues: {
      MICROSOFT_CLIENT_ID: config["MICROSOFT_CLIENT_ID"],
      MICROSOFT_CLIENT_SECRET: config["MICROSOFT_CLIENT_SECRET"],
      MICROSOFT_TENANT_ID: config["MICROSOFT_TENANT_ID"],
      ENABLE_MICROSOFT_SYNC: config["ENABLE_MICROSOFT_SYNC"] || "0",
    },
  });

  const originURL = !isEmpty(API_BASE_URL) ? API_BASE_URL : typeof window !== "undefined" ? window.location.origin : "";

  const MICROSOFT_FORM_FIELDS: TControllerInputFormField[] = [
    {
      key: "MICROSOFT_CLIENT_ID",
      type: "text",
      label: "Client ID",
      description: (
        <>
          Your client (application) ID lives in your Azure App Registration.{" "}
          <a
            href="https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app"
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
            aria-label="Microsoft Entra ID app registration documentation"
          >
            Learn more
          </a>
        </>
      ),
      placeholder: "c2e5c1f0-6b3a-4b7e-9c2e-8f1a2b3c4d5e",
      error: Boolean(errors.MICROSOFT_CLIENT_ID),
      required: true,
    },
    {
      key: "MICROSOFT_CLIENT_SECRET",
      type: "password",
      label: "Client secret",
      description: (
        <>
          Create a client secret under <CodeBlock darkerShade>Certificates &amp; secrets</CodeBlock> in your Azure App
          Registration.
        </>
      ),
      placeholder: "8Q~1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q",
      error: Boolean(errors.MICROSOFT_CLIENT_SECRET),
      required: true,
    },
    {
      key: "MICROSOFT_TENANT_ID",
      type: "text",
      label: "Tenant ID",
      description: (
        <>
          Your Azure AD directory (tenant) ID. Use <CodeBlock darkerShade>common</CodeBlock> to allow sign-in from any
          Microsoft account.
        </>
      ),
      placeholder: "9e8d7c6b-5a4f-3e2d-1c0b-a9b8c7d6e5f4",
      error: Boolean(errors.MICROSOFT_TENANT_ID),
      required: true,
    },
  ];

  const MICROSOFT_COMMON_SERVICE_DETAILS: TCopyField[] = [
    {
      key: "Origin_URL",
      label: "Origin URL",
      url: originURL,
      description: (
        <p>
          We will auto-generate this. Paste this into your <CodeBlock darkerShade>Redirect URIs</CodeBlock> field. For
          this app registration{" "}
          <a
            href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
            aria-label="Azure Portal app registrations"
          >
            here.
          </a>
        </p>
      ),
    },
  ];

  const MICROSOFT_SERVICE_DETAILS: TCopyField[] = [
    {
      key: "Callback_URI",
      label: "Callback URI",
      url: `${originURL}/auth/microsoft/callback/`,
      description: (
        <p>
          We will auto-generate this. Paste this into your <CodeBlock darkerShade>Redirect URIs</CodeBlock> field. For
          this app registration{" "}
          <a
            href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
            aria-label="Azure Portal app registrations"
          >
            here.
          </a>
        </p>
      ),
    },
  ];

  const onSubmit = async (formData: MicrosoftConfigFormValues) => {
    const payload: Partial<MicrosoftConfigFormValues> = { ...formData };

    try {
      const response = await updateInstanceConfigurations(payload);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Done!",
        message: "Your Microsoft authentication is configured. You should test it now.",
      });
      reset({
        MICROSOFT_CLIENT_ID: response.find((item) => item.key === "MICROSOFT_CLIENT_ID")?.value,
        MICROSOFT_CLIENT_SECRET: response.find((item) => item.key === "MICROSOFT_CLIENT_SECRET")?.value,
        MICROSOFT_TENANT_ID: response.find((item) => item.key === "MICROSOFT_TENANT_ID")?.value,
        ENABLE_MICROSOFT_SYNC: response.find((item) => item.key === "ENABLE_MICROSOFT_SYNC")?.value,
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleGoBack = (e: React.MouseEvent<HTMLAnchorElement, MouseEvent>) => {
    if (isDirty) {
      e.preventDefault();
      setIsDiscardChangesModalOpen(true);
    }
  };

  return (
    <>
      <ConfirmDiscardModal
        isOpen={isDiscardChangesModalOpen}
        onDiscardHref="/authentication"
        handleClose={() => setIsDiscardChangesModalOpen(false)}
      />
      <div className="flex flex-col gap-8">
        <div className="grid w-full grid-cols-2 gap-x-12 gap-y-8">
          <div className="col-span-2 flex flex-col gap-y-4 pt-1 md:col-span-1">
            <div className="pt-2.5 text-18 font-medium">Microsoft-provided details for Plane</div>
            {MICROSOFT_FORM_FIELDS.map((field) => (
              <ControllerInput
                key={field.key}
                control={control}
                type={field.type}
                name={field.key}
                label={field.label}
                description={field.description}
                placeholder={field.placeholder}
                error={field.error}
                required={field.required}
              />
            ))}
            <ControllerSwitch control={control} field={MICROSOFT_FORM_SWITCH_FIELD} />
            <div className="flex flex-col gap-1 pt-4">
              <div className="flex items-center gap-4">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={(e) => void handleSubmit(onSubmit)(e)}
                  loading={isSubmitting}
                  disabled={!isDirty}
                >
                  {isSubmitting ? "Saving" : "Save changes"}
                </Button>
                <Link href="/authentication" className={getButtonStyling("secondary", "lg")} onClick={handleGoBack}>
                  Go back
                </Link>
              </div>
            </div>
          </div>
          <div className="col-span-2 flex flex-col gap-y-6 md:col-span-1">
            <div className="pt-2 text-18 font-medium">Plane-provided details for Microsoft</div>

            <div className="flex flex-col gap-y-4">
              {/* common service details */}
              <div className="flex flex-col gap-y-4 rounded-lg bg-layer-1 px-6 py-4">
                {MICROSOFT_COMMON_SERVICE_DETAILS.map((field) => (
                  <CopyField key={field.key} label={field.label} url={field.url} description={field.description} />
                ))}
              </div>

              {/* web service details */}
              <div className="flex flex-col overflow-hidden rounded-lg">
                <div className="flex items-center gap-x-3 bg-layer-3 px-6 py-3 text-11 font-medium text-secondary uppercase">
                  Redirect URI
                </div>
                <div className="flex flex-col gap-y-4 bg-layer-1 px-6 py-4">
                  {MICROSOFT_SERVICE_DETAILS.map((field) => (
                    <CopyField key={field.key} label={field.label} url={field.url} description={field.description} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
