CREATE TABLE "django_migrations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app" varchar(255) NOT NULL, "name" varchar(255) NOT NULL, "applied" datetime NOT NULL);

CREATE TABLE "auth_group_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "auth_user_groups" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "auth_user_user_permissions" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE UNIQUE INDEX "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" ON "auth_group_permissions" ("group_id", "permission_id");

CREATE INDEX "auth_group_permissions_group_id_b120cbf9" ON "auth_group_permissions" ("group_id");

CREATE INDEX "auth_group_permissions_permission_id_84c5c92e" ON "auth_group_permissions" ("permission_id");

CREATE UNIQUE INDEX "auth_user_groups_user_id_group_id_94350c0c_uniq" ON "auth_user_groups" ("user_id", "group_id");

CREATE INDEX "auth_user_groups_user_id_6a12ed8b" ON "auth_user_groups" ("user_id");

CREATE INDEX "auth_user_groups_group_id_97559544" ON "auth_user_groups" ("group_id");

CREATE UNIQUE INDEX "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq" ON "auth_user_user_permissions" ("user_id", "permission_id");

CREATE INDEX "auth_user_user_permissions_user_id_a95ead1b" ON "auth_user_user_permissions" ("user_id");

CREATE INDEX "auth_user_user_permissions_permission_id_1fbb5f2c" ON "auth_user_user_permissions" ("permission_id");

CREATE TABLE "django_admin_log" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "object_id" text NULL, "object_repr" varchar(200) NOT NULL, "action_flag" smallint unsigned NOT NULL CHECK ("action_flag" >= 0), "change_message" text NOT NULL, "content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "action_time" datetime NOT NULL);

CREATE INDEX "django_admin_log_content_type_id_c4bce8eb" ON "django_admin_log" ("content_type_id");

CREATE INDEX "django_admin_log_user_id_c564eba6" ON "django_admin_log" ("user_id");

CREATE TABLE "django_content_type" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app_label" varchar(100) NOT NULL, "model" varchar(100) NOT NULL);

CREATE UNIQUE INDEX "django_content_type_app_label_model_76bd3d3b_uniq" ON "django_content_type" ("app_label", "model");

CREATE TABLE "auth_permission" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "content_type_id" integer NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED, "codename" varchar(100) NOT NULL, "name" varchar(255) NOT NULL);

CREATE UNIQUE INDEX "auth_permission_content_type_id_codename_01ab375a_uniq" ON "auth_permission" ("content_type_id", "codename");

CREATE INDEX "auth_permission_content_type_id_2f476e4b" ON "auth_permission" ("content_type_id");

CREATE TABLE "auth_group" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(150) NOT NULL UNIQUE);

CREATE TABLE "auth_user" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "password" varchar(128) NOT NULL, "last_login" datetime NULL, "is_superuser" bool NOT NULL, "username" varchar(150) NOT NULL UNIQUE, "last_name" varchar(150) NOT NULL, "email" varchar(254) NOT NULL, "is_staff" bool NOT NULL, "is_active" bool NOT NULL, "date_joined" datetime NOT NULL, "first_name" varchar(150) NOT NULL);

CREATE TABLE "babyspa_data_branch" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "location_id" integer NOT NULL UNIQUE, "branch_name" varchar(100) NOT NULL, "city" varchar(100) NOT NULL);

CREATE TABLE "babyspa_data_customer" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "erp_id" integer NOT NULL UNIQUE, "name" varchar(255) NOT NULL, "date_of_birth" date NULL, "gender" bool NULL);

CREATE TABLE "django_session" ("session_key" varchar(40) NOT NULL PRIMARY KEY, "session_data" text NOT NULL, "expire_date" datetime NOT NULL);

CREATE INDEX "django_session_expire_date_a5c62663" ON "django_session" ("expire_date");

CREATE TABLE "babyspa_data_transactionitem" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "quantity" integer NOT NULL, "product_id" char(32) NOT NULL REFERENCES "babyspa_data_product" ("id") DEFERRABLE INITIALLY DEFERRED, "transaction_id" char(32) NOT NULL REFERENCES "babyspa_data_transaction" ("id") DEFERRABLE INITIALLY DEFERRED, "status" varchar(50) NOT NULL, "ref_number" varchar(50) NULL, "scheduled_date" datetime NULL, "duration" real NULL, "sale_price" real NULL);

CREATE INDEX "babyspa_data_transactionitem_product_id_05f20530" ON "babyspa_data_transactionitem" ("product_id");

CREATE INDEX "babyspa_data_transactionitem_transaction_id_8237f9fa" ON "babyspa_data_transactionitem" ("transaction_id");

CREATE TABLE "babyspa_data_transaction" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "scheduled_date" datetime NOT NULL, "total_price" real NOT NULL, "status" varchar(50) NOT NULL, "branch_id" char(32) NOT NULL REFERENCES "babyspa_data_branch" ("id") DEFERRABLE INITIALLY DEFERRED, "customer_id" char(32) NOT NULL REFERENCES "babyspa_data_customer" ("id") DEFERRABLE INITIALLY DEFERRED, "ref_number" varchar(50) NULL);

CREATE INDEX "babyspa_data_transaction_branch_id_4a09600e" ON "babyspa_data_transaction" ("branch_id");

CREATE INDEX "babyspa_data_transaction_customer_id_e7d8b1b0" ON "babyspa_data_transaction" ("customer_id");

CREATE TABLE "babyspa_data_ahpconfiguration" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "name" varchar(100) NOT NULL, "context" varchar(20) NOT NULL, "w_length" real NULL, "w_recency" real NOT NULL, "w_frequency" real NOT NULL, "w_monetary" real NOT NULL);

CREATE TABLE "babyspa_data_lrfmreference" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "symbol" varchar(10) NOT NULL UNIQUE, "group_name" varchar(100) NOT NULL, "main_category" varchar(100) NOT NULL, "description" text NULL, "recommendation" text NULL);

CREATE TABLE "babyspa_data_clusterlrfm" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "cluster_id" integer NOT NULL, "mean_length" real NOT NULL, "mean_recency" real NOT NULL, "mean_frequency" real NOT NULL, "mean_monetary" real NOT NULL, "ahp_config_id" char(32) NULL REFERENCES "babyspa_data_ahpconfiguration" ("id") DEFERRABLE INITIALLY DEFERRED, "lrfm_reference_id" char(32) NOT NULL REFERENCES "babyspa_data_lrfmreference" ("id") DEFERRABLE INITIALLY DEFERRED, "k_value" integer NULL, "max_discount_percent" real NULL, "min_discount_percent" real NULL);

CREATE INDEX "babyspa_data_clusterlrfm_ahp_config_id_2354461b" ON "babyspa_data_clusterlrfm" ("ahp_config_id");

CREATE INDEX "babyspa_data_clusterlrfm_lrfm_reference_id_60d8de12" ON "babyspa_data_clusterlrfm" ("lrfm_reference_id");

CREATE TABLE "babyspa_data_productrecommendation" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "support" real NOT NULL, "confidence" real NOT NULL, "lift" real NOT NULL, "rank_n" integer NOT NULL, "cluster_lrfm_id" char(32) NULL REFERENCES "babyspa_data_clusterlrfm" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "babyspa_data_productrecommendation_cluster_lrfm_id_f4394294" ON "babyspa_data_productrecommendation" ("cluster_lrfm_id");

CREATE TABLE "babyspa_data_productrecommendation_antecedent" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "productrecommendation_id" char(32) NOT NULL REFERENCES "babyspa_data_productrecommendation" ("id") DEFERRABLE INITIALLY DEFERRED, "product_id" char(32) NOT NULL REFERENCES "babyspa_data_product" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE TABLE "babyspa_data_productrecommendation_consequent" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "productrecommendation_id" char(32) NOT NULL REFERENCES "babyspa_data_productrecommendation" ("id") DEFERRABLE INITIALLY DEFERRED, "product_id" char(32) NOT NULL REFERENCES "babyspa_data_product" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE UNIQUE INDEX "babyspa_data_productrecommendation_antecedent_productrecommendation_id_product_id_8f47c852_uniq" ON "babyspa_data_productrecommendation_antecedent" ("productrecommendation_id", "product_id");

CREATE INDEX "babyspa_data_productrecommendation_antecedent_productrecommendation_id_9628ae8f" ON "babyspa_data_productrecommendation_antecedent" ("productrecommendation_id");

CREATE INDEX "babyspa_data_productrecommendation_antecedent_product_id_5a4de388" ON "babyspa_data_productrecommendation_antecedent" ("product_id");

CREATE UNIQUE INDEX "babyspa_data_productrecommendation_consequent_productrecommendation_id_product_id_6d907be0_uniq" ON "babyspa_data_productrecommendation_consequent" ("productrecommendation_id", "product_id");

CREATE INDEX "babyspa_data_productrecommendation_consequent_productrecommendation_id_188edb5c" ON "babyspa_data_productrecommendation_consequent" ("productrecommendation_id");

CREATE INDEX "babyspa_data_productrecommendation_consequent_product_id_efbd4013" ON "babyspa_data_productrecommendation_consequent" ("product_id");

CREATE TABLE "babyspa_data_productscore" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "r_normalized" real NOT NULL, "f_normalized" real NOT NULL, "m_normalized" real NOT NULL, "total_saw_score" real NOT NULL, "rank" integer NOT NULL, "is_top_n" bool NOT NULL, "ahp_config_id" char(32) NULL REFERENCES "babyspa_data_ahpconfiguration" ("id") DEFERRABLE INITIALLY DEFERRED, "product_id" char(32) NOT NULL REFERENCES "babyspa_data_product" ("id") DEFERRABLE INITIALLY DEFERRED, "cluster_id_id" char(32) NULL REFERENCES "babyspa_data_clusterlrfm" ("id") DEFERRABLE INITIALLY DEFERRED, "name" varchar(255) NULL);

CREATE INDEX "babyspa_data_productscore_ahp_config_id_118cc4a4" ON "babyspa_data_productscore" ("ahp_config_id");

CREATE INDEX "babyspa_data_productscore_product_id_730940cd" ON "babyspa_data_productscore" ("product_id");

CREATE INDEX "babyspa_data_productscore_cluster_id_id_d2f0390d" ON "babyspa_data_productscore" ("cluster_id_id");

CREATE TABLE "babyspa_data_customersegment" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "clv_score" real NOT NULL, "is_churn" bool NOT NULL, "customer_id" char(32) NOT NULL REFERENCES "babyspa_data_customer" ("id") DEFERRABLE INITIALLY DEFERRED, "cluster_lrfm_id" char(32) NULL REFERENCES "babyspa_data_clusterlrfm" ("id") DEFERRABLE INITIALLY DEFERRED, "f_normalized" real NOT NULL, "f_real" real NOT NULL, "l_normalized" real NOT NULL, "l_real" real NOT NULL, "m_normalized" real NOT NULL, "m_real" real NOT NULL, "r_normalized" real NOT NULL, "r_real" real NOT NULL, "age" integer NOT NULL);

CREATE INDEX "babyspa_data_customersegment_customer_id_283ee4e5" ON "babyspa_data_customersegment" ("customer_id");

CREATE INDEX "babyspa_data_customersegment_cluster_lrfm_id_da9a849b" ON "babyspa_data_customersegment" ("cluster_lrfm_id");

CREATE TABLE "babyspa_data_productcategory" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "name" varchar(100) NOT NULL UNIQUE, "slug" varchar(100) NULL UNIQUE, "description" text NULL);

CREATE TABLE "babyspa_data_product" ("id" char(32) NOT NULL PRIMARY KEY, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "deleted_at" datetime NULL, "item_name" varchar(255) NOT NULL, "retail_price" real NOT NULL, "is_addon" bool NOT NULL, "erp_item_id" integer NULL UNIQUE, "description" text NULL, "category_id" char(32) NULL REFERENCES "babyspa_data_productcategory" ("id") DEFERRABLE INITIALLY DEFERRED, "master_product_id" char(32) NULL REFERENCES "babyspa_data_product" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE INDEX "babyspa_data_product_category_id_9c576615" ON "babyspa_data_product" ("category_id");

CREATE INDEX "babyspa_data_product_master_product_id_ce3908cd" ON "babyspa_data_product" ("master_product_id");

CREATE TABLE "babyspa_data_product_branches" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "product_id" char(32) NOT NULL REFERENCES "babyspa_data_product" ("id") DEFERRABLE INITIALLY DEFERRED, "branch_id" char(32) NOT NULL REFERENCES "babyspa_data_branch" ("id") DEFERRABLE INITIALLY DEFERRED);

CREATE UNIQUE INDEX "babyspa_data_product_branches_product_id_branch_id_7d21a46f_uniq" ON "babyspa_data_product_branches" ("product_id", "branch_id");

CREATE INDEX "babyspa_data_product_branches_product_id_6f403f5f" ON "babyspa_data_product_branches" ("product_id");

CREATE INDEX "babyspa_data_product_branches_branch_id_03ea8888" ON "babyspa_data_product_branches" ("branch_id");